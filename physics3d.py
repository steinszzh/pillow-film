# -*- coding: utf-8 -*-
"""物理增强软件 3D 渲染器 v2。
新增：细分曲面与顶点法线、Blinn-Phong 镜面/菲涅尔、平方反比衰减、filmlike 色调映射、
透明面混合、按光源方向投影的软阴影、体积光束、重力雨滴、按深度的景深、超采样抗锯齿。
所有几何仍由代码生成，无模型文件 / 无 3D 库 / 无生成式图像模型。
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from draw import glow
from scene3d import camera, project_points, BG

W,H = 1280,720
SS = 1.25                                   # 超采样倍率
IW,IH = int(W*SS), int(H*SS)

# 材质：(金属度, 粗糙度, 透明度)
MAT = dict(
    cloth=(.02,.94,0), wall=(.00,.88,0), wood=(.04,.72,0), paint=(.22,.48,0),
    metal=(.86,.24,0), steel=(.72,.34,0), glass=(.10,.08,.62), water=(.16,.06,.45),
    paper=(.00,.90,0), skin=(.06,.68,0), dark=(.10,.60,0), screen=(.30,.22,0),
    rubber=(.02,.86,0), tile=(.08,.55,0),
)

def C(r,g,b): return (float(r),float(g),float(b))
WALL=C(.125,.145,.165); WALL2=C(.095,.112,.128); FLOOR=C(.095,.09,.09)
CEIL=C(.075,.085,.095); DOOR=C(.115,.155,.185); DOOR_DK=C(.052,.068,.085)
WOOD=C(.255,.175,.125); WOOD_D=C(.15,.11,.085)
BLUE=C(.115,.275,.415); BLUE_D=C(.075,.17,.265)
GREY=C(.235,.255,.265); GREY_D=C(.145,.165,.175)
SKIN=C(.235,.205,.185); DARK=C(.045,.06,.075)
GLASS=C(.33,.52,.58); WATER=C(.19,.37,.44); SILVER=C(.46,.52,.55)
RED=C(.33,.125,.105); PAPER=C(.60,.58,.53); GREEN=C(.17,.56,.45)
AMB=C(.105,.125,.155)

def _r(rx=0,ry=0,rz=0):
    cx,sx=math.cos(rx),math.sin(rx); cy,sy=math.cos(ry),math.sin(ry); cz,sz=math.cos(rz),math.sin(rz)
    return (np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]) @
            np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @
            np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]))

class Geo:
    """面统一 4 顶点；每面带材质、顶点法线、是否受光"""
    def __init__(self):
        self.v=[]; self.c=[]; self.em=[]; self.mat=[]; self.vn=[]; self.unlit=[]
        self.lights=[]; self.shadows=[]; self.glows=[]; self.ui=[]; self.rain=None

    def face(self, verts, col, mat='wall', em=(0,0,0), vn=None, unlit=False):
        pts=list(verts)
        if len(pts)==3: pts=pts+[pts[2]]
        self.v.append(np.array(pts,np.float32))
        self.c.append(col); self.em.append(em)
        self.mat.append(MAT.get(mat,MAT['wall']) if isinstance(mat,str) else mat)
        self.vn.append(np.array(vn,np.float32) if vn is not None else None)
        self.unlit.append(unlit)

    def box(self,c,s,col,mat='wall',rot=(0,0,0),em=(0,0,0),bevel=0.0):
        cx,cy,cz=c; sx,sy,sz=s
        x0,x1=cx-sx/2,cx+sx/2; y0,y1=cy-sy/2,cy+sy/2; z0,z1=cz-sz/2,cz+sz/2
        pts=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
                      [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]],np.float32)
        if any(rot): pts=(pts-np.array(c))@_r(*rot).T+np.array(c)
        p=[tuple(v) for v in pts]
        for f in ([p[0],p[1],p[2],p[3]],[p[5],p[4],p[7],p[6]],
                  [p[4],p[0],p[3],p[7]],[p[1],p[5],p[6],p[2]],
                  [p[3],p[2],p[6],p[7]],[p[4],p[5],p[1],p[0]]):
            self.face(f,col,mat=mat,em=em)
        if bevel>0:   # 顶面一圈细高光，近似倒角
            b=bevel
            self.face([(p[3][0]+b,p[3][1],p[3][2]+b),(p[2][0]-b,p[2][1],p[2][2]+b),
                       (p[6][0]-b,p[6][1],p[6][2]-b),(p[7][0]+b,p[7][1],p[7][2]-b)],
                      tuple(min(1,q*1.35) for q in col),mat='paint')

    def frustum(self,c,r0,r1,h,sides=14,col=GREY,mat='cloth',em=(0,0,0),close=True):
        """锥台：r0 底半径 r1 顶半径，径向顶点法线 → 平滑着色"""
        cx,cy,cz=c; y0,y1=cy-h/2,cy+h/2
        ang=[2*math.pi*i/sides for i in range(sides)]
        bot=[(cx+r0*math.cos(a),y0,cz+r0*math.sin(a)) for a in ang]
        top=[(cx+r1*math.cos(a),y1,cz+r1*math.sin(a)) for a in ang]
        for i in range(sides):
            j=(i+1)%sides
            nb=[(math.cos(ang[i]),0,math.sin(ang[i])),(math.cos(ang[j]),0,math.sin(ang[j]))]
            self.face([bot[i],bot[j],top[j],top[i]],col,mat=mat,em=em,
                      vn=[nb[0],nb[1],nb[1],nb[0]])
            if close:
                self.face([(cx,y1,cz),top[i],top[j],top[j]],tuple(q*1.12 for q in col),mat=mat,em=em)
                self.face([(cx,y0,cz),bot[j],bot[i],bot[i]],tuple(q*.72 for q in col),mat=mat,em=em)

    def tube(self,c,r,h,sides=16,col=GLASS,mat='glass',thick=.012):
        """薄壁管（玻璃杯）：外壁透明 + 内壁 + 口沿高光"""
        cx,cy,cz=c; y0,y1=cy-h/2,cy+h/2
        ang=[2*math.pi*i/sides for i in range(sides)]
        for i in range(sides):
            j=(i+1)%sides
            a0,a1=ang[i],ang[j]
            def pt(a,rr,y): return (cx+rr*math.cos(a),y,cz+rr*math.sin(a))
            n0=(math.cos(a0),0,math.sin(a0)); n1=(math.cos(a1),0,math.sin(a1))
            self.face([pt(a0,r,y0),pt(a1,r,y0),pt(a1,r,y1),pt(a0,r,y1)],col,mat=mat,
                      vn=[n0,n1,n1,n0])
            self.face([pt(a1,r-thick,y0),pt(a0,r-thick,y0),pt(a0,r-thick,y1),pt(a1,r-thick,y1)],
                      tuple(q*.72 for q in col),mat=mat,vn=[n1,n0,n0,n1])
            self.face([pt(a0,r,y1),pt(a1,r,y1),pt(a1,r-thick,y1),pt(a0,r-thick,y1)],
                      tuple(min(1,q*1.7) for q in col),mat='steel')

    def sphere(self,c,r,col,mat='skin',lat=8,lon=14):
        """经纬球：顶点法线 = 半径方向，高光连续"""
        cx,cy,cz=c
        def P(theta,phi):
            return (cx+r*math.sin(theta)*math.cos(phi), cy+r*math.cos(theta),
                    cz+r*math.sin(theta)*math.sin(phi))
        for i in range(lat):
            t0,t1=math.pi*i/lat,math.pi*(i+1)/lat
            for j in range(lon):
                p0,p1=2*math.pi*j/lon,2*math.pi*(j+1)/lon
                q=[P(t0,p0),P(t0,p1),P(t1,p1),P(t1,p0)]
                vn=[tuple((np.array(v)-np.array(c))/r) for v in q]
                self.face(q,col,mat=mat,vn=vn)

    def disc(self,c,r,col,mat='water',sides=16,up=True):
        cx,cy,cz=c
        ang=[2*math.pi*i/sides for i in range(sides)]
        for i in range(sides):
            j=(i+1)%sides
            a,b=ang[i],ang[j]
            self.face([(cx,cy,cz),(cx+r*math.cos(a),cy,cz+r*math.sin(a)),
                       (cx+r*math.cos(b),cy,cz+r*math.sin(b)),(cx+r*math.cos(b),cy,cz+r*math.sin(b))],
                      col,mat=mat,vn=[(0,1,0)]*4 if up else [(0,-1,0)]*4)

    def beam(self,quad,col,alpha=.07,layers=3):
        """体积光柱：多层半透明四边形，unlit 直接给色"""
        for k in range(layers):
            self.face(quad,col,mat=(0,.9,alpha/layers),unlit=True)

    def light(self,pos,col,intensity=1.0,radius=6.0,glow=None):
        self.lights.append((np.array(pos,np.float32),np.array(col,np.float32),intensity,radius))
        if glow: self.glows.append((pos,glow[0],glow[1],glow[2]))

    def shadow(self,x,z,h=1.7,size=.4): self.shadows.append((x,z,h,size))
    def ui(self,anchor,kind,p): self.ui.append((anchor,kind,p))
    def rain_volume(self,box,n=150,g=9.8): self.rain=(box,n,g)

    def merge(self,o):
        for k in ('v','c','em','mat','vn','unlit','lights','shadows','glows','ui'):
            getattr(self,k).extend(getattr(o,k))
        if o.rain: self.rain=o.rain
        return self

# ---------------------------------------------------------------- 物理渲染
def _shadow_faces(g):
    """按光源方向把物体轮廓投影到地面，三层扩张形成软阴影"""
    out=Geo()
    for (x,z,h,size) in g.shadows:
        for lp,lc,inte,rad in g.lights[:2]:
            dx,dz=x-lp[0],z-lp[2]
            L=max(.5,math.hypot(dx,dz))
            ux,uz=dx/L,dz/L
            stretch=min(1.4,h*L/(max(lp[1],.5)*3.0))
            for k,(sc,al) in enumerate(((1.0,.16),(1.35,.10),(1.75,.055))):
                pts=[]
                for i in range(12):
                    a=2*math.pi*i/12
                    rx=size*sc*(1+stretch*.8)*math.cos(a)
                    rz=size*sc*math.sin(a)
                    # 沿光方向拉长
                    px=x+rx*ux-rz*uz + ux*stretch*.25
                    pz=z+rx*uz+rz*ux + uz*stretch*.25
                    pts.append((px,.008+k*.001,pz))
                for i in range(12):
                    j=(i+1)%12
                    out.face([(x,.009+k*.001,z),pts[i],pts[j],pts[j]],(0,0,0),
                             mat=(0,.9,al),unlit=True)
    return out

def render_v2(g, eye, target, fov, t=0.0, flick=1.0, dof=True, focus=None, dof_range=3.2,
              return_bake=False):
    cam=camera(eye,target,fov,IW,IH)
    img=Image.new('RGB',(IW,IH),BG)
    def _empty():
        return dict(v=[],c=[],a=[],u=[],eye=[round(float(q),3) for q in eye],
                    target=[round(float(q),3) for q in target],fov=round(float(fov),2))
    if not g.v:
        o=img.resize((W,H),Image.LANCZOS); return (o,_empty()) if return_bake else o
    # 阴影几何并入同一深度排序
    sh=_shadow_faces(g)
    V=np.stack(g.v+sh.v); Cols=np.array(g.c+sh.c,np.float32)
    Ems=np.array(g.em+sh.em,np.float32); Mats=np.array(g.mat+sh.mat,np.float32)
    Unlit=np.array(g.unlit+sh.unlit)
    VN=g.vn+sh.vn
    eyev=cam[0]
    S,Z=project_points(V.reshape(-1,3),cam)
    S=S.reshape(-1,4,2); Z=Z.reshape(-1,4)
    ok=(Z>.06).all(axis=1)&(S[:,:,0].max(axis=1)>-400)&(S[:,:,0].min(axis=1)<IW+400)\
       &(S[:,:,1].max(axis=1)>-400)&(S[:,:,1].min(axis=1)<IH+400)
    idx=np.nonzero(ok)[0]
    if not len(idx):
        o=img.resize((W,H),Image.LANCZOS); return (o,_empty()) if return_bake else o
    S,Z,Cols,Ems,Mats,Unlit,V=S[idx],Z[idx],Cols[idx],Ems[idx],Mats[idx],Unlit[idx],V[idx]
    VN=[VN[i] for i in idx]
    depth=Z.mean(axis=1); center=V.mean(axis=1)
    # 法线：优先顶点法线（平滑），否则面法线并翻向相机
    n=np.cross(V[:,1]-V[:,0],V[:,2]-V[:,0])
    n=n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-6)
    for i,vn in enumerate(VN):
        if vn is not None:
            nn=vn.mean(axis=0); q=np.linalg.norm(nn)
            if q>1e-6: n[i]=nn/q
    to_eye=eyev-center
    v=to_eye/np.maximum(np.linalg.norm(to_eye,axis=1,keepdims=True),1e-6)
    flip=np.einsum('ij,ij->i',n,to_eye)<0
    n[flip]*=-1
    metal=Mats[:,0:1]; rough=Mats[:,1:2]; alpha=Mats[:,2:3]

    col=Cols*np.array(AMB,np.float32)+Ems
    for lp,lc,inte,rad in g.lights:
        lv=lp-center; dist=np.linalg.norm(lv,axis=1,keepdims=True)
        ld=lv/np.maximum(dist,1e-4)
        atten=(rad*rad)/(dist*dist+rad*rad)          # 平方反比衰减（带软化）
        lam=np.clip(np.einsum('ij,ij->i',n,ld),0,1)[:,None]
        col+=Cols*lc[None,:]*(lam*inte*atten*flick)
        hv=ld+v; hv=hv/np.maximum(np.linalg.norm(hv,axis=1,keepdims=True),1e-6)
        spec=np.clip(np.einsum('ij,ij->i',n,hv),0,1)**(2.0/(rough*rough+.02)+2)
        col+=lc[None,:]*(spec[:,None]*(.05+.9*metal)*inte*atten*flick)
    fres=(1-np.clip(np.einsum('ij,ij->i',n,v),0,1))**4
    col+=fres[:,None]*(.035+.55*metal)*np.array([.48,.62,.72],np.float32)[None,:]
    fog=np.clip((depth-6.0)/20.0,0,.46)[:,None]
    col=col*(1-fog)+np.array(BG,np.float32)[None,:]/255*fog
    # filmlike 色调映射（避免高光死白）
    col=col/(col+np.float32(.78))*np.float32(1.42)
    col[Unlit]=Cols[Unlit]+Ems[Unlit]
    col8=np.clip(col*255,0,255).astype(np.uint8)

    # 景深遮罩：按面与焦平面的距离给出模糊权重
    focus=float(np.linalg.norm(np.array(target)-np.array(eye))) if focus is None else focus
    coc=np.clip(np.abs(depth-focus)/dof_range,0,1)*150
    mask=Image.new('L',(IW,IH),0); md=ImageDraw.Draw(mask)
    dr=ImageDraw.Draw(img); drA=ImageDraw.Draw(img,'RGBA')
    order=np.argsort(-depth)
    for i in order:
        pts=[(int(S[i,j,0]),int(S[i,j,1])) for j in range(4)]
        cc=tuple(int(q) for q in col8[i])
        a=float(alpha[i,0])
        if a>0:
            drA.polygon(pts,fill=(*cc,int(a*255)))
        else:
            dr.polygon(pts,fill=cc,outline=tuple(max(0,int(q*.52)) for q in col8[i]),width=1)
        md.polygon(pts,fill=int(coc[i]))
    if dof:
        blur=img.filter(ImageFilter.GaussianBlur(2.4))
        img=Image.composite(blur,img,mask)
    else:
        md=None

    # 光源光晕（屏幕空间）
    for (pos,gcol,gsize,strength) in g.glows:
        s,zz=project_points(np.array([pos],np.float32),cam)
        if zz[0]>.06:
            size=max(20,min(1600,int(gsize/max(zz[0],1.0))))
            gl=glow(size,gcol,2.6,strength*flick)
            img.paste(gl,(int(s[0,0]-size/2),int(s[0,1]-size/2)),gl)

    # 体积雨：世界空间自由落体，速度决定拖影长度，近大远小
    if g.rain:
        box,n,grav=g.rain
        x0,x1,y0,y1,z0=box
        rng=np.random.default_rng(119)
        px=rng.uniform(x0,x1,n); pz=rng.uniform(z0,z0+.35,n); ph=rng.uniform(0,1,n)
        fall=math.sqrt(2*max(y1-y0,.1)/grav)
        tau=(t*1.6+ph*fall)%fall
        py=y1-.5*grav*tau*tau
        speed=grav*tau
        P0,_=project_points(np.stack([px,py,pz],axis=1),cam)
        P1,_=project_points(np.stack([px-.02,py-np.clip(speed*.012,.02,.22),pz],axis=1),cam)
        rd=ImageDraw.Draw(img,'RGBA')
        for i in range(n):
            if speed[i]<.4: continue
            a=int(np.clip(28+speed[i]*16,0,110))
            rd.line([(P0[i,0],P0[i,1]),(P1[i,0],P1[i,1])],fill=(120,164,184,a),width=1)
        # 落地水花
        for i in range(0,n,9):
            if py[i]<y0+.04:
                s2,zz=project_points(np.array([[px[i],y0+.01,pz[i]]],np.float32),cam)
                if zz[0]>.06:
                    rd.ellipse((s2[0,0]-3,s2[0,1]-1,s2[0,0]+3,s2[0,1]+1),fill=(150,190,204,60))
    out=img.resize((W,H),Image.LANCZOS)
    if return_bake:
        bake=dict(v=np.round(V,2).tolist(), c=col8.tolist(),
                  a=np.round(Mats[:,2],3).tolist(), u=Unlit.astype(bool).tolist(),
                  eye=[round(float(q),3) for q in eye],
                  target=[round(float(q),3) for q in target], fov=round(float(fov),2))
        return out,bake
    return out
