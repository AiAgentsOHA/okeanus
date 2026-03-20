"use strict";(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[114],{24540:e=>{function t(e,t,u){u=u||2;var d,f,v,x,y,m,P,_=t&&t.length,C=_?t[0]*u:e.length,L=i(e,0,C,u,!0),b=[];if(!L||L.next===L.prev)return b;if(_&&(L=function(e,t,s,l){var c,u,d,f,h,v=[];for(c=0,u=t.length;c<u;c++)d=t[c]*l,f=c<u-1?t[c+1]*l:e.length,(h=i(e,d,f,l,!1))===h.next&&(h.steiner=!0),v.push(function(e){var t=e,i=e;do(t.x<i.x||t.x===i.x&&t.y<i.y)&&(i=t),t=t.next;while(t!==e);return i}(h));for(v.sort(n),c=0;c<v.length;c++)s=function(e,t){var i=function(e,t){var i,o,n,s=t,l=e.x,c=e.y,u=-1/0;do{if(c<=s.y&&c>=s.next.y&&s.next.y!==s.y){var d=s.x+(c-s.y)*(s.next.x-s.x)/(s.next.y-s.y);if(d<=l&&d>u&&(u=d,n=s.x<s.next.x?s:s.next,d===l))return n}s=s.next}while(s!==t);if(!n)return null;var g,f=n,h=n.x,v=n.y,x=1/0;s=n;do l>=s.x&&s.x>=h&&l!==s.x&&r(c<v?l:u,c,h,v,c<v?u:l,c,s.x,s.y)&&(g=Math.abs(c-s.y)/(l-s.x),p(s,e)&&(g<x||g===x&&(s.x>n.x||s.x===n.x&&(i=n,o=s,0>a(i.prev,i,o.prev)&&0>a(o.next,i,i.next))))&&(n=s,x=g)),s=s.next;while(s!==f);return n}(e,t);if(!i)return t;var n=g(i,e);return o(n,n.next),o(i,i.next)}(v[c],s);return s}(e,t,L,u)),e.length>80*u){d=v=e[0],f=x=e[1];for(var S=u;S<C;S+=u)y=e[S],m=e[S+1],y<d&&(d=y),m<f&&(f=m),y>v&&(v=y),m>x&&(x=m);P=0!==(P=Math.max(v-d,x-f))?32767/P:0}return function e(t,i,n,u,d,f,v){if(t){!v&&f&&function(e,t,i,o){var n=e;do 0===n.z&&(n.z=s(n.x,n.y,t,i,o)),n.prevZ=n.prev,n.nextZ=n.next,n=n.next;while(n!==e);n.prevZ.nextZ=null,n.prevZ=null,function(e){var t,i,o,n,s,r,a,l,c=1;do{for(i=e,e=null,s=null,r=0;i;){for(r++,o=i,a=0,t=0;t<c&&(a++,o=o.nextZ);t++);for(l=c;a>0||l>0&&o;)0!==a&&(0===l||!o||i.z<=o.z)?(n=i,i=i.nextZ,a--):(n=o,o=o.nextZ,l--),s?s.nextZ=n:e=n,n.prevZ=s,s=n;i=o}s.nextZ=null,c*=2}while(r>1)}(n)}(t,u,d,f);for(var x,y,m=t;t.prev!==t.next;){if(x=t.prev,y=t.next,f?function(e,t,i,o){var n=e.prev,l=e.next;if(a(n,e,l)>=0)return!1;for(var c=n.x,u=e.x,d=l.x,p=n.y,g=e.y,f=l.y,h=c<u?c<d?c:d:u<d?u:d,v=p<g?p<f?p:f:g<f?g:f,x=c>u?c>d?c:d:u>d?u:d,y=p>g?p>f?p:f:g>f?g:f,m=s(h,v,t,i,o),P=s(x,y,t,i,o),_=e.prevZ,C=e.nextZ;_&&_.z>=m&&C&&C.z<=P;){if(_.x>=h&&_.x<=x&&_.y>=v&&_.y<=y&&_!==n&&_!==l&&r(c,p,u,g,d,f,_.x,_.y)&&a(_.prev,_,_.next)>=0||(_=_.prevZ,C.x>=h&&C.x<=x&&C.y>=v&&C.y<=y&&C!==n&&C!==l&&r(c,p,u,g,d,f,C.x,C.y)&&a(C.prev,C,C.next)>=0))return!1;C=C.nextZ}for(;_&&_.z>=m;){if(_.x>=h&&_.x<=x&&_.y>=v&&_.y<=y&&_!==n&&_!==l&&r(c,p,u,g,d,f,_.x,_.y)&&a(_.prev,_,_.next)>=0)return!1;_=_.prevZ}for(;C&&C.z<=P;){if(C.x>=h&&C.x<=x&&C.y>=v&&C.y<=y&&C!==n&&C!==l&&r(c,p,u,g,d,f,C.x,C.y)&&a(C.prev,C,C.next)>=0)return!1;C=C.nextZ}return!0}(t,u,d,f):function(e){var t=e.prev,i=e.next;if(a(t,e,i)>=0)return!1;for(var o=t.x,n=e.x,s=i.x,l=t.y,c=e.y,u=i.y,d=o<n?o<s?o:s:n<s?n:s,p=l<c?l<u?l:u:c<u?c:u,g=o>n?o>s?o:s:n>s?n:s,f=l>c?l>u?l:u:c>u?c:u,h=i.next;h!==t;){if(h.x>=d&&h.x<=g&&h.y>=p&&h.y<=f&&r(o,l,n,c,s,u,h.x,h.y)&&a(h.prev,h,h.next)>=0)return!1;h=h.next}return!0}(t)){i.push(x.i/n|0),i.push(t.i/n|0),i.push(y.i/n|0),h(t),t=y.next,m=y.next;continue}if((t=y)===m){v?1===v?e(t=function(e,t,i){var n=e;do{var s=n.prev,r=n.next.next;!l(s,r)&&c(s,n,n.next,r)&&p(s,r)&&p(r,s)&&(t.push(s.i/i|0),t.push(n.i/i|0),t.push(r.i/i|0),h(n),h(n.next),n=e=r),n=n.next}while(n!==e);return o(n)}(o(t),i,n),i,n,u,d,f,2):2===v&&function(t,i,n,s,r,u){var d=t;do{for(var f,h,v=d.next.next;v!==d.prev;){if(d.i!==v.i&&(f=d,h=v,f.next.i!==h.i&&f.prev.i!==h.i&&!function(e,t){var i=e;do{if(i.i!==e.i&&i.next.i!==e.i&&i.i!==t.i&&i.next.i!==t.i&&c(i,i.next,e,t))return!0;i=i.next}while(i!==e);return!1}(f,h)&&(p(f,h)&&p(h,f)&&function(e,t){var i=e,o=!1,n=(e.x+t.x)/2,s=(e.y+t.y)/2;do i.y>s!=i.next.y>s&&i.next.y!==i.y&&n<(i.next.x-i.x)*(s-i.y)/(i.next.y-i.y)+i.x&&(o=!o),i=i.next;while(i!==e);return o}(f,h)&&(a(f.prev,f,h.prev)||a(f,h.prev,h))||l(f,h)&&a(f.prev,f,f.next)>0&&a(h.prev,h,h.next)>0))){var x=g(d,v);d=o(d,d.next),x=o(x,x.next),e(d,i,n,s,r,u,0),e(x,i,n,s,r,u,0);return}v=v.next}d=d.next}while(d!==t)}(t,i,n,u,d,f):e(o(t),i,n,u,d,f,1);break}}}}(L,b,u,d,f,P,0),b}function i(e,t,i,o,n){var s,r;if(n===x(e,t,i,o)>0)for(s=t;s<i;s+=o)r=f(s,e[s],e[s+1],r);else for(s=i-o;s>=t;s-=o)r=f(s,e[s],e[s+1],r);return r&&l(r,r.next)&&(h(r),r=r.next),r}function o(e,t){if(!e)return e;t||(t=e);var i,o=e;do if(i=!1,!o.steiner&&(l(o,o.next)||0===a(o.prev,o,o.next))){if(h(o),(o=t=o.prev)===o.next)break;i=!0}else o=o.next;while(i||o!==t);return t}function n(e,t){return e.x-t.x}function s(e,t,i,o,n){return(e=((e=((e=((e=((e=(e-i)*n|0)|e<<8)&0xff00ff)|e<<4)&0xf0f0f0f)|e<<2)&0x33333333)|e<<1)&0x55555555)|(t=((t=((t=((t=((t=(t-o)*n|0)|t<<8)&0xff00ff)|t<<4)&0xf0f0f0f)|t<<2)&0x33333333)|t<<1)&0x55555555)<<1}function r(e,t,i,o,n,s,r,a){return(n-r)*(t-a)>=(e-r)*(s-a)&&(e-r)*(o-a)>=(i-r)*(t-a)&&(i-r)*(s-a)>=(n-r)*(o-a)}function a(e,t,i){return(t.y-e.y)*(i.x-t.x)-(t.x-e.x)*(i.y-t.y)}function l(e,t){return e.x===t.x&&e.y===t.y}function c(e,t,i,o){var n=d(a(e,t,i)),s=d(a(e,t,o)),r=d(a(i,o,e)),l=d(a(i,o,t));return!!(n!==s&&r!==l||0===n&&u(e,i,t)||0===s&&u(e,o,t)||0===r&&u(i,e,o)||0===l&&u(i,t,o))}function u(e,t,i){return t.x<=Math.max(e.x,i.x)&&t.x>=Math.min(e.x,i.x)&&t.y<=Math.max(e.y,i.y)&&t.y>=Math.min(e.y,i.y)}function d(e){return e>0?1:e<0?-1:0}function p(e,t){return 0>a(e.prev,e,e.next)?a(e,t,e.next)>=0&&a(e,e.prev,t)>=0:0>a(e,t,e.prev)||0>a(e,e.next,t)}function g(e,t){var i=new v(e.i,e.x,e.y),o=new v(t.i,t.x,t.y),n=e.next,s=t.prev;return e.next=t,t.prev=e,i.next=n,n.prev=i,o.next=i,i.prev=o,s.next=o,o.prev=s,o}function f(e,t,i,o){var n=new v(e,t,i);return o?(n.next=o.next,n.prev=o,o.next.prev=n,o.next=n):(n.prev=n,n.next=n),n}function h(e){e.next.prev=e.prev,e.prev.next=e.next,e.prevZ&&(e.prevZ.nextZ=e.nextZ),e.nextZ&&(e.nextZ.prevZ=e.prevZ)}function v(e,t,i){this.i=e,this.x=t,this.y=i,this.prev=null,this.next=null,this.z=0,this.prevZ=null,this.nextZ=null,this.steiner=!1}function x(e,t,i,o){for(var n=0,s=t,r=i-o;s<i;s+=o)n+=(e[r]-e[s])*(e[s+1]+e[r+1]),r=s;return n}e.exports=t,e.exports.default=t,t.deviation=function(e,t,i,o){var n=t&&t.length,s=n?t[0]*i:e.length,r=Math.abs(x(e,0,s,i));if(n)for(var a=0,l=t.length;a<l;a++){var c=t[a]*i,u=a<l-1?t[a+1]*i:e.length;r-=Math.abs(x(e,c,u,i))}var d=0;for(a=0;a<o.length;a+=3){var p=o[a]*i,g=o[a+1]*i,f=o[a+2]*i;d+=Math.abs((e[p]-e[f])*(e[g+1]-e[p+1])-(e[p]-e[g])*(e[f+1]-e[p+1]))}return 0===r&&0===d?0:Math.abs((d-r)/r)},t.flatten=function(e){for(var t=e[0][0].length,i={vertices:[],holes:[],dimensions:t},o=0,n=0;n<e.length;n++){for(var s=0;s<e[n].length;s++)for(var r=0;r<t;r++)i.vertices.push(e[n][s][r]);n>0&&(o+=e[n-1].length,i.holes.push(o))}return i}},78604:(e,t,i)=>{i.d(t,{A:()=>h});var o=i(98318),n=i(2854),s=i(65489),r=i(60303),a=i(91538);let l=`\
uniform arcUniforms {
  bool greatCircle;
  bool useShortestPath;
  float numSegments;
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  highp int widthUnits;
} arc;
`,c={name:"arc",vs:l,fs:l,uniformTypes:{greatCircle:"f32",useShortestPath:"f32",numSegments:"f32",widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",widthUnits:"i32"}},u=`\
#version 300 es
#define SHADER_NAME arc-layer-vertex-shader
in vec4 instanceSourceColors;
in vec4 instanceTargetColors;
in vec3 instanceSourcePositions;
in vec3 instanceSourcePositions64Low;
in vec3 instanceTargetPositions;
in vec3 instanceTargetPositions64Low;
in vec3 instancePickingColors;
in float instanceWidths;
in float instanceHeights;
in float instanceTilts;
out vec4 vColor;
out vec2 uv;
out float isValid;
float paraboloid(float distance, float sourceZ, float targetZ, float ratio) {
float deltaZ = targetZ - sourceZ;
float dh = distance * instanceHeights;
if (dh == 0.0) {
return sourceZ + deltaZ * ratio;
}
float unitZ = deltaZ / dh;
float p2 = unitZ * unitZ + 1.0;
float dir = step(deltaZ, 0.0);
float z0 = mix(sourceZ, targetZ, dir);
float r = mix(ratio, 1.0 - ratio, dir);
return sqrt(r * (p2 - r)) * dh + z0;
}
vec2 getExtrusionOffset(vec2 line_clipspace, float offset_direction, float width) {
vec2 dir_screenspace = normalize(line_clipspace * project.viewportSize);
dir_screenspace = vec2(-dir_screenspace.y, dir_screenspace.x);
return dir_screenspace * offset_direction * width / 2.0;
}
float getSegmentRatio(float index) {
return smoothstep(0.0, 1.0, index / (arc.numSegments - 1.0));
}
vec3 interpolateFlat(vec3 source, vec3 target, float segmentRatio) {
float distance = length(source.xy - target.xy);
float z = paraboloid(distance, source.z, target.z, segmentRatio);
float tiltAngle = radians(instanceTilts);
vec2 tiltDirection = normalize(target.xy - source.xy);
vec2 tilt = vec2(-tiltDirection.y, tiltDirection.x) * z * sin(tiltAngle);
return vec3(
mix(source.xy, target.xy, segmentRatio) + tilt,
z * cos(tiltAngle)
);
}
float getAngularDist (vec2 source, vec2 target) {
vec2 sourceRadians = radians(source);
vec2 targetRadians = radians(target);
vec2 sin_half_delta = sin((sourceRadians - targetRadians) / 2.0);
vec2 shd_sq = sin_half_delta * sin_half_delta;
float a = shd_sq.y + cos(sourceRadians.y) * cos(targetRadians.y) * shd_sq.x;
return 2.0 * asin(sqrt(a));
}
vec3 interpolateGreatCircle(vec3 source, vec3 target, vec3 source3D, vec3 target3D, float angularDist, float t) {
vec2 lngLat;
if(abs(angularDist - PI) < 0.001) {
lngLat = (1.0 - t) * source.xy + t * target.xy;
} else {
float a = sin((1.0 - t) * angularDist);
float b = sin(t * angularDist);
vec3 p = source3D.yxz * a + target3D.yxz * b;
lngLat = degrees(vec2(atan(p.y, -p.x), atan(p.z, length(p.xy))));
}
float z = paraboloid(angularDist * EARTH_RADIUS, source.z, target.z, t);
return vec3(lngLat, z);
}
void main(void) {
geometry.worldPosition = instanceSourcePositions;
geometry.worldPositionAlt = instanceTargetPositions;
float segmentIndex = float(gl_VertexID / 2);
float segmentSide = mod(float(gl_VertexID), 2.) == 0. ? -1. : 1.;
float segmentRatio = getSegmentRatio(segmentIndex);
float prevSegmentRatio = getSegmentRatio(max(0.0, segmentIndex - 1.0));
float nextSegmentRatio = getSegmentRatio(min(arc.numSegments - 1.0, segmentIndex + 1.0));
float indexDir = mix(-1.0, 1.0, step(segmentIndex, 0.0));
isValid = 1.0;
uv = vec2(segmentRatio, segmentSide);
geometry.uv = uv;
geometry.pickingColor = instancePickingColors;
vec4 curr;
vec4 next;
vec3 source;
vec3 target;
if ((arc.greatCircle || project.projectionMode == PROJECTION_MODE_GLOBE) && project.coordinateSystem == COORDINATE_SYSTEM_LNGLAT) {
source = project_globe_(vec3(instanceSourcePositions.xy, 0.0));
target = project_globe_(vec3(instanceTargetPositions.xy, 0.0));
float angularDist = getAngularDist(instanceSourcePositions.xy, instanceTargetPositions.xy);
vec3 prevPos = interpolateGreatCircle(instanceSourcePositions, instanceTargetPositions, source, target, angularDist, prevSegmentRatio);
vec3 currPos = interpolateGreatCircle(instanceSourcePositions, instanceTargetPositions, source, target, angularDist, segmentRatio);
vec3 nextPos = interpolateGreatCircle(instanceSourcePositions, instanceTargetPositions, source, target, angularDist, nextSegmentRatio);
if (abs(currPos.x - prevPos.x) > 180.0) {
indexDir = -1.0;
isValid = 0.0;
} else if (abs(currPos.x - nextPos.x) > 180.0) {
indexDir = 1.0;
isValid = 0.0;
}
nextPos = indexDir < 0.0 ? prevPos : nextPos;
nextSegmentRatio = indexDir < 0.0 ? prevSegmentRatio : nextSegmentRatio;
if (isValid == 0.0) {
nextPos.x += nextPos.x > 0.0 ? -360.0 : 360.0;
float t = ((currPos.x > 0.0 ? 180.0 : -180.0) - currPos.x) / (nextPos.x - currPos.x);
currPos = mix(currPos, nextPos, t);
segmentRatio = mix(segmentRatio, nextSegmentRatio, t);
}
vec3 currPos64Low = mix(instanceSourcePositions64Low, instanceTargetPositions64Low, segmentRatio);
vec3 nextPos64Low = mix(instanceSourcePositions64Low, instanceTargetPositions64Low, nextSegmentRatio);
curr = project_position_to_clipspace(currPos, currPos64Low, vec3(0.0), geometry.position);
next = project_position_to_clipspace(nextPos, nextPos64Low, vec3(0.0));
} else {
vec3 source_world = instanceSourcePositions;
vec3 target_world = instanceTargetPositions;
if (arc.useShortestPath) {
source_world.x = mod(source_world.x + 180., 360.0) - 180.;
target_world.x = mod(target_world.x + 180., 360.0) - 180.;
float deltaLng = target_world.x - source_world.x;
if (deltaLng > 180.) target_world.x -= 360.;
if (deltaLng < -180.) source_world.x -= 360.;
}
source = project_position(source_world, instanceSourcePositions64Low);
target = project_position(target_world, instanceTargetPositions64Low);
float antiMeridianX = 0.0;
if (arc.useShortestPath) {
if (project.projectionMode == PROJECTION_MODE_WEB_MERCATOR_AUTO_OFFSET) {
antiMeridianX = -(project.coordinateOrigin.x + 180.) / 360. * TILE_SIZE;
}
float thresholdRatio = (antiMeridianX - source.x) / (target.x - source.x);
if (prevSegmentRatio <= thresholdRatio && nextSegmentRatio > thresholdRatio) {
isValid = 0.0;
indexDir = sign(segmentRatio - thresholdRatio);
segmentRatio = thresholdRatio;
}
}
nextSegmentRatio = indexDir < 0.0 ? prevSegmentRatio : nextSegmentRatio;
vec3 currPos = interpolateFlat(source, target, segmentRatio);
vec3 nextPos = interpolateFlat(source, target, nextSegmentRatio);
if (arc.useShortestPath) {
if (nextPos.x < antiMeridianX) {
currPos.x += TILE_SIZE;
nextPos.x += TILE_SIZE;
}
}
curr = project_common_position_to_clipspace(vec4(currPos, 1.0));
next = project_common_position_to_clipspace(vec4(nextPos, 1.0));
geometry.position = vec4(currPos, 1.0);
}
float widthPixels = clamp(
project_size_to_pixel(instanceWidths * arc.widthScale, arc.widthUnits),
arc.widthMinPixels, arc.widthMaxPixels
);
vec3 offset = vec3(
getExtrusionOffset((next.xy - curr.xy) * indexDir, segmentSide, widthPixels),
0.0);
DECKGL_FILTER_SIZE(offset, geometry);
DECKGL_FILTER_GL_POSITION(curr, geometry);
gl_Position = curr + vec4(project_pixel_size_to_clipspace(offset.xy), 0.0, 0.0);
vec4 color = mix(instanceSourceColors, instanceTargetColors, segmentRatio);
vColor = vec4(color.rgb, color.a * layer.opacity);
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,d=`\
#version 300 es
#define SHADER_NAME arc-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 uv;
in float isValid;
out vec4 fragColor;
void main(void) {
if (isValid == 0.0) {
discard;
}
fragColor = vColor;
geometry.uv = uv;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,p=[0,0,0,255],g={getSourcePosition:{type:"accessor",value:e=>e.sourcePosition},getTargetPosition:{type:"accessor",value:e=>e.targetPosition},getSourceColor:{type:"accessor",value:p},getTargetColor:{type:"accessor",value:p},getWidth:{type:"accessor",value:1},getHeight:{type:"accessor",value:1},getTilt:{type:"accessor",value:0},greatCircle:!1,numSegments:{type:"number",value:50,min:1},widthUnits:"pixels",widthScale:{type:"number",value:1,min:0},widthMinPixels:{type:"number",value:0,min:0},widthMaxPixels:{type:"number",value:Number.MAX_SAFE_INTEGER,min:0}};class f extends o.A{getBounds(){return this.getAttributeManager()?.getBounds(["instanceSourcePositions","instanceTargetPositions"])}getShaders(){return super.getShaders({vs:u,fs:d,modules:[n.A,s.A,c]})}get wrapLongitude(){return!1}initializeState(){this.getAttributeManager().addInstanced({instanceSourcePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getSourcePosition"},instanceTargetPositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getTargetPosition"},instanceSourceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getSourceColor",defaultValue:p},instanceTargetColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getTargetColor",defaultValue:p},instanceWidths:{size:1,transition:!0,accessor:"getWidth",defaultValue:1},instanceHeights:{size:1,transition:!0,accessor:"getHeight",defaultValue:1},instanceTilts:{size:1,transition:!0,accessor:"getTilt",defaultValue:0}})}updateState(e){super.updateState(e),e.changeFlags.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:e}){let{widthUnits:t,widthScale:i,widthMinPixels:o,widthMaxPixels:n,greatCircle:s,wrapLongitude:a,numSegments:l}=this.props,c={numSegments:l,widthUnits:r.p5[t],widthScale:i,widthMinPixels:o,widthMaxPixels:n,greatCircle:s,useShortestPath:a},u=this.state.model;u.shaderInputs.setProps({arc:c}),u.setVertexCount(2*l),u.draw(this.context.renderPass)}_getModel(){return new a.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),topology:"triangle-strip",isInstanced:!0})}}f.layerName="ArcLayer",f.defaultProps=g;let h=f},82978:(e,t,i)=>{i.d(t,{A:()=>m});var o=i(60303),n=i(98318),s=i(2854),r=i(65489),a=i(91538),l=i(36706),c=i(21108);let u=new Uint32Array([0,2,1,0,3,2]),d=new Float32Array([0,1,0,0,1,0,1,1]),p=`\
uniform bitmapUniforms {
  vec4 bounds;
  float coordinateConversion;
  float desaturate;
  vec3 tintColor;
  vec4 transparentColor;
} bitmap;
`,g={name:"bitmap",vs:p,fs:p,uniformTypes:{bounds:"vec4<f32>",coordinateConversion:"f32",desaturate:"f32",tintColor:"vec3<f32>",transparentColor:"vec4<f32>"}},f=`\
#version 300 es
#define SHADER_NAME bitmap-layer-vertex-shader

in vec2 texCoords;
in vec3 positions;
in vec3 positions64Low;

out vec2 vTexCoord;
out vec2 vTexPos;

const vec3 pickingColor = vec3(1.0, 0.0, 0.0);

void main(void) {
  geometry.worldPosition = positions;
  geometry.uv = texCoords;
  geometry.pickingColor = pickingColor;

  gl_Position = project_position_to_clipspace(positions, positions64Low, vec3(0.0), geometry.position);
  DECKGL_FILTER_GL_POSITION(gl_Position, geometry);

  vTexCoord = texCoords;

  if (bitmap.coordinateConversion < -0.5) {
    vTexPos = geometry.position.xy + project.commonOrigin.xy;
  } else if (bitmap.coordinateConversion > 0.5) {
    vTexPos = geometry.worldPosition.xy;
  }

  vec4 color = vec4(0.0);
  DECKGL_FILTER_COLOR(color, geometry);
}
`,h=`
vec3 packUVsIntoRGB(vec2 uv) {
  // Extract the top 8 bits. We want values to be truncated down so we can add a fraction
  vec2 uv8bit = floor(uv * 256.);

  // Calculate the normalized remainders of u and v parts that do not fit into 8 bits
  // Scale and clamp to 0-1 range
  vec2 uvFraction = fract(uv * 256.);
  vec2 uvFraction4bit = floor(uvFraction * 16.);

  // Remainder can be encoded in blue channel, encode as 4 bits for pixel coordinates
  float fractions = uvFraction4bit.x + uvFraction4bit.y * 16.;

  return vec3(uv8bit, fractions) / 255.;
}
`,v=`\
#version 300 es
#define SHADER_NAME bitmap-layer-fragment-shader

#ifdef GL_ES
precision highp float;
#endif

uniform sampler2D bitmapTexture;

in vec2 vTexCoord;
in vec2 vTexPos;

out vec4 fragColor;

/* projection utils */
const float TILE_SIZE = 512.0;
const float PI = 3.1415926536;
const float WORLD_SCALE = TILE_SIZE / PI / 2.0;

// from degrees to Web Mercator
vec2 lnglat_to_mercator(vec2 lnglat) {
  float x = lnglat.x;
  float y = clamp(lnglat.y, -89.9, 89.9);
  return vec2(
    radians(x) + PI,
    PI + log(tan(PI * 0.25 + radians(y) * 0.5))
  ) * WORLD_SCALE;
}

// from Web Mercator to degrees
vec2 mercator_to_lnglat(vec2 xy) {
  xy /= WORLD_SCALE;
  return degrees(vec2(
    xy.x - PI,
    atan(exp(xy.y - PI)) * 2.0 - PI * 0.5
  ));
}
/* End projection utils */

// apply desaturation
vec3 color_desaturate(vec3 color) {
  float luminance = (color.r + color.g + color.b) * 0.333333333;
  return mix(color, vec3(luminance), bitmap.desaturate);
}

// apply tint
vec3 color_tint(vec3 color) {
  return color * bitmap.tintColor;
}

// blend with background color
vec4 apply_opacity(vec3 color, float alpha) {
  if (bitmap.transparentColor.a == 0.0) {
    return vec4(color, alpha);
  }
  float blendedAlpha = alpha + bitmap.transparentColor.a * (1.0 - alpha);
  float highLightRatio = alpha / blendedAlpha;
  vec3 blendedRGB = mix(bitmap.transparentColor.rgb, color, highLightRatio);
  return vec4(blendedRGB, blendedAlpha);
}

vec2 getUV(vec2 pos) {
  return vec2(
    (pos.x - bitmap.bounds[0]) / (bitmap.bounds[2] - bitmap.bounds[0]),
    (pos.y - bitmap.bounds[3]) / (bitmap.bounds[1] - bitmap.bounds[3])
  );
}

${h}

void main(void) {
  vec2 uv = vTexCoord;
  if (bitmap.coordinateConversion < -0.5) {
    vec2 lnglat = mercator_to_lnglat(vTexPos);
    uv = getUV(lnglat);
  } else if (bitmap.coordinateConversion > 0.5) {
    vec2 commonPos = lnglat_to_mercator(vTexPos);
    uv = getUV(commonPos);
  }
  vec4 bitmapColor = texture(bitmapTexture, uv);

  fragColor = apply_opacity(color_tint(color_desaturate(bitmapColor.rgb)), bitmapColor.a * layer.opacity);

  geometry.uv = uv;
  DECKGL_FILTER_COLOR(fragColor, geometry);

  if (bool(picking.isActive) && !bool(picking.isAttribute)) {
    // Since instance information is not used, we can use picking color for pixel index
    fragColor.rgb = packUVsIntoRGB(uv);
  }
}
`,x={image:{type:"image",value:null,async:!0},bounds:{type:"array",value:[1,0,0,1],compare:!0},_imageCoordinateSystem:o.rf.DEFAULT,desaturate:{type:"number",min:0,max:1,value:0},transparentColor:{type:"color",value:[0,0,0,0]},tintColor:{type:"color",value:[255,255,255]},textureParameters:{type:"object",ignore:!0,value:null}};class y extends n.A{getShaders(){return super.getShaders({vs:f,fs:v,modules:[s.A,r.A,g]})}initializeState(){let e=this.getAttributeManager();e.remove(["instancePickingColors"]),e.add({indices:{size:1,isIndexed:!0,update:e=>e.value=this.state.mesh.indices,noAlloc:!0},positions:{size:3,type:"float64",fp64:this.use64bitPositions(),update:e=>e.value=this.state.mesh.positions,noAlloc:!0},texCoords:{size:2,update:e=>e.value=this.state.mesh.texCoords,noAlloc:!0}})}updateState({props:e,oldProps:t,changeFlags:i}){let o=this.getAttributeManager();if(i.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),o.invalidateAll()),e.bounds!==t.bounds){let e=this.state.mesh,t=this._createMesh();for(let i in this.state.model.setVertexCount(t.vertexCount),t)e&&e[i]!==t[i]&&o.invalidate(i);this.setState({mesh:t,...this._getCoordinateUniforms()})}else e._imageCoordinateSystem!==t._imageCoordinateSystem&&this.setState(this._getCoordinateUniforms())}getPickingInfo(e){let{image:t}=this.props,i=e.info;if(!i.color||!t)return i.bitmap=null,i;let{width:o,height:n}=t;i.index=0;let s=function(e){let[t,i,o]=e;return[(t+(15&o)/16)/256,(i+(240&o)/256)/256]}(i.color);return i.bitmap={size:{width:o,height:n},uv:s,pixel:[Math.floor(s[0]*o),Math.floor(s[1]*n)]},i}disablePickingIndex(){this.setState({disablePicking:!0})}restorePickingColors(){this.setState({disablePicking:!1})}_updateAutoHighlight(e){super._updateAutoHighlight({...e,color:this.encodePickingColor(0)})}_createMesh(){let{bounds:e}=this.props,t=e;return P(e)&&(t=[[e[0],e[1]],[e[0],e[3]],[e[2],e[3]],[e[2],e[1]]]),function(e,t){if(!t)return function(e){let t=new Float64Array(12);for(let i=0;i<e.length;i++)t[3*i+0]=e[i][0],t[3*i+1]=e[i][1],t[3*i+2]=e[i][2]||0;return{vertexCount:6,positions:t,indices:u,texCoords:d}}(e);let i=Math.max(Math.abs(e[0][0]-e[3][0]),Math.abs(e[1][0]-e[2][0])),o=Math.max(Math.abs(e[1][1]-e[0][1]),Math.abs(e[2][1]-e[3][1])),n=Math.ceil(i/t)+1,s=Math.ceil(o/t)+1,r=(n-1)*(s-1)*6,a=new Uint32Array(r),l=new Float32Array(n*s*2),p=new Float64Array(n*s*3),g=0,f=0;for(let t=0;t<n;t++){let i=t/(n-1);for(let o=0;o<s;o++){let n=o/(s-1),r=(0,c.Cc)((0,c.Cc)(e[0],e[1],n),(0,c.Cc)(e[3],e[2],n),i);p[3*g+0]=r[0],p[3*g+1]=r[1],p[3*g+2]=r[2]||0,l[2*g+0]=i,l[2*g+1]=1-n,t>0&&o>0&&(a[f++]=g-s,a[f++]=g-s-1,a[f++]=g-1,a[f++]=g-s,a[f++]=g-1,a[f++]=g),g++}}return{vertexCount:r,positions:p,indices:a,texCoords:l}}(t,this.context.viewport.resolution)}_getModel(){return new a.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),topology:"triangle-list",isInstanced:!1})}draw(e){let{shaderModuleProps:t}=e,{model:i,coordinateConversion:o,bounds:n,disablePicking:s}=this.state,{image:r,desaturate:a,transparentColor:l,tintColor:c}=this.props;if((!t.picking.isActive||!s)&&r&&i){let e={bitmapTexture:r,bounds:n,coordinateConversion:o,desaturate:a,tintColor:c.slice(0,3).map(e=>e/255),transparentColor:l.map(e=>e/255)};i.shaderInputs.setProps({bitmap:e}),i.draw(this.context.renderPass)}}_getCoordinateUniforms(){let{LNGLAT:e,CARTESIAN:t,DEFAULT:i}=o.rf,{_imageCoordinateSystem:n}=this.props;if(n!==i){let{bounds:i}=this.props;if(!P(i))throw Error("_imageCoordinateSystem only supports rectangular bounds");let o=this.context.viewport.resolution?e:t;if((n=n===e?e:t)===e&&o===t)return{coordinateConversion:-1,bounds:i};if(n===t&&o===e){let e=(0,l.Gw)([i[0],i[1]]),t=(0,l.Gw)([i[2],i[3]]);return{coordinateConversion:1,bounds:[e[0],e[1],t[0],t[1]]}}}return{coordinateConversion:0,bounds:[0,0,0,0]}}}y.layerName="BitmapLayer",y.defaultProps=x;let m=y;function P(e){return Number.isFinite(e[0])}},70640:(e,t,i)=>{i.d(t,{A:()=>_});var o=i(98318),n=i(2854),s=i(65489),r=i(60303),a=i(4387),l=i(75817),c=i(91538),u=i(77002),d=i(88912),p=i(95952);class g extends d.V{constructor(e){let{indices:t,attributes:i}=function(e){let{radius:t,height:i=1,nradial:o=10}=e,{vertices:n}=e;n&&(u.A.assert(n.length>=o),n=n.flatMap(e=>[e[0],e[1]]),(0,p.UD)(n,p.rJ.COUNTER_CLOCKWISE));let s=i>0,r=o+1,a=s?3*r+1:o,l=2*Math.PI/o,c=new Uint16Array(s?6*o:0),d=new Float32Array(3*a),g=new Float32Array(3*a),f=0;if(s){for(let e=0;e<r;e++){let s=e*l,r=e%o,a=Math.sin(s),c=Math.cos(s);for(let e=0;e<2;e++)d[f+0]=n?n[2*r]:c*t,d[f+1]=n?n[2*r+1]:a*t,d[f+2]=(.5-e)*i,g[f+0]=n?n[2*r]:c,g[f+1]=n?n[2*r+1]:a,f+=3}d[f+0]=d[f-3],d[f+1]=d[f-2],d[f+2]=d[f-1],f+=3}for(let e=s?0:1;e<r;e++){let s=Math.floor(e/2)*Math.sign(.5-e%2),r=s*l,a=(s+o)%o,c=Math.sin(r),u=Math.cos(r);d[f+0]=n?n[2*a]:u*t,d[f+1]=n?n[2*a+1]:c*t,d[f+2]=i/2,g[f+2]=1,f+=3}if(s){let e=0;for(let t=0;t<o;t++)c[e++]=2*t+0,c[e++]=2*t+2,c[e++]=2*t+0,c[e++]=2*t+1,c[e++]=2*t+1,c[e++]=2*t+3}return{indices:c,attributes:{POSITION:{size:3,value:d},NORMAL:{size:3,value:g}}}}(e);super({...e,indices:t,attributes:i})}}let f=`\
uniform columnUniforms {
  float radius;
  float angle;
  vec2 offset;
  bool extruded;
  bool stroked;
  bool isStroke;
  float coverage;
  float elevationScale;
  float edgeDistance;
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  highp int radiusUnits;
  highp int widthUnits;
} column;
`,h={name:"column",vs:f,fs:f,uniformTypes:{radius:"f32",angle:"f32",offset:"vec2<f32>",extruded:"f32",stroked:"f32",isStroke:"f32",coverage:"f32",elevationScale:"f32",edgeDistance:"f32",widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",radiusUnits:"i32",widthUnits:"i32"}},v=`#version 300 es
#define SHADER_NAME column-layer-vertex-shader
in vec3 positions;
in vec3 normals;
in vec3 instancePositions;
in float instanceElevations;
in vec3 instancePositions64Low;
in vec4 instanceFillColors;
in vec4 instanceLineColors;
in float instanceStrokeWidths;
in vec3 instancePickingColors;
out vec4 vColor;
#ifdef FLAT_SHADING
out vec3 cameraPosition;
out vec4 position_commonspace;
#endif
void main(void) {
geometry.worldPosition = instancePositions;
vec4 color = column.isStroke ? instanceLineColors : instanceFillColors;
mat2 rotationMatrix = mat2(cos(column.angle), sin(column.angle), -sin(column.angle), cos(column.angle));
float elevation = 0.0;
float strokeOffsetRatio = 1.0;
if (column.extruded) {
elevation = instanceElevations * (positions.z + 1.0) / 2.0 * column.elevationScale;
} else if (column.stroked) {
float widthPixels = clamp(
project_size_to_pixel(instanceStrokeWidths * column.widthScale, column.widthUnits),
column.widthMinPixels, column.widthMaxPixels) / 2.0;
float halfOffset = project_pixel_size(widthPixels) / project_size(column.edgeDistance * column.coverage * column.radius);
if (column.isStroke) {
strokeOffsetRatio -= sign(positions.z) * halfOffset;
} else {
strokeOffsetRatio -= halfOffset;
}
}
float shouldRender = float(color.a > 0.0 && instanceElevations >= 0.0);
float dotRadius = column.radius * column.coverage * shouldRender;
geometry.pickingColor = instancePickingColors;
vec3 centroidPosition = vec3(instancePositions.xy, instancePositions.z + elevation);
vec3 centroidPosition64Low = instancePositions64Low;
vec2 offset = (rotationMatrix * positions.xy * strokeOffsetRatio + column.offset) * dotRadius;
if (column.radiusUnits == UNIT_METERS) {
offset = project_size(offset);
} else if (column.radiusUnits == UNIT_PIXELS) {
offset = project_pixel_size(offset);
}
vec3 pos = vec3(offset, 0.);
DECKGL_FILTER_SIZE(pos, geometry);
gl_Position = project_position_to_clipspace(centroidPosition, centroidPosition64Low, pos, geometry.position);
geometry.normal = project_normal(vec3(rotationMatrix * normals.xy, normals.z));
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
if (column.extruded && !column.isStroke) {
#ifdef FLAT_SHADING
cameraPosition = project.cameraPosition;
position_commonspace = geometry.position;
vColor = vec4(color.rgb, color.a * layer.opacity);
#else
vec3 lightColor = lighting_getLightColor(color.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);
vColor = vec4(lightColor, color.a * layer.opacity);
#endif
} else {
vColor = vec4(color.rgb, color.a * layer.opacity);
}
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,x=`#version 300 es
#define SHADER_NAME column-layer-fragment-shader
precision highp float;
out vec4 fragColor;
in vec4 vColor;
#ifdef FLAT_SHADING
in vec3 cameraPosition;
in vec4 position_commonspace;
#endif
void main(void) {
fragColor = vColor;
geometry.uv = vec2(0.);
#ifdef FLAT_SHADING
if (column.extruded && !column.isStroke && !bool(picking.isActive)) {
vec3 normal = normalize(cross(dFdx(position_commonspace.xyz), dFdy(position_commonspace.xyz)));
fragColor.rgb = lighting_getLightColor(vColor.rgb, cameraPosition, position_commonspace.xyz, normal);
}
#endif
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,y=[0,0,0,255],m={diskResolution:{type:"number",min:4,value:20},vertices:null,radius:{type:"number",min:0,value:1e3},angle:{type:"number",value:0},offset:{type:"array",value:[0,0]},coverage:{type:"number",min:0,max:1,value:1},elevationScale:{type:"number",min:0,value:1},radiusUnits:"meters",lineWidthUnits:"meters",lineWidthScale:1,lineWidthMinPixels:0,lineWidthMaxPixels:Number.MAX_SAFE_INTEGER,extruded:!0,wireframe:!1,filled:!0,stroked:!1,flatShading:!1,getPosition:{type:"accessor",value:e=>e.position},getFillColor:{type:"accessor",value:y},getLineColor:{type:"accessor",value:y},getLineWidth:{type:"accessor",value:1},getElevation:{type:"accessor",value:1e3},material:!0,getColor:{deprecatedFor:["getFillColor","getLineColor"]}};class P extends o.A{getShaders(){let e={},{flatShading:t}=this.props;return t&&(e.FLAT_SHADING=1),super.getShaders({vs:v,fs:x,defines:e,modules:[n.A,t?a.w:l.J,s.A,h]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceElevations:{size:1,transition:!0,accessor:"getElevation"},instanceFillColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getFillColor",defaultValue:y},instanceLineColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getLineColor",defaultValue:y},instanceStrokeWidths:{size:1,accessor:"getLineWidth",transition:!0}})}updateState(e){super.updateState(e);let{props:t,oldProps:i,changeFlags:o}=e,n=o.extensionsChanged||t.flatShading!==i.flatShading;n&&(this.state.models?.forEach(e=>e.destroy()),this.setState(this._getModels()),this.getAttributeManager().invalidateAll());let s=this.getNumInstances();this.state.fillModel.setInstanceCount(s),this.state.wireframeModel.setInstanceCount(s),(n||t.diskResolution!==i.diskResolution||t.vertices!==i.vertices||(t.extruded||t.stroked)!==(i.extruded||i.stroked))&&this._updateGeometry(t)}getGeometry(e,t,i){let o=new g({radius:1,height:i?2:0,vertices:t,nradial:e}),n=0;if(t)for(let i=0;i<e;i++){let o=t[i];n+=Math.sqrt(o[0]*o[0]+o[1]*o[1])/e}else n=1;return this.setState({edgeDistance:Math.cos(Math.PI/e)*n}),o}_getModels(){let e=this.getShaders(),t=this.getAttributeManager().getBufferLayouts(),i=new c.K(this.context.device,{...e,id:`${this.props.id}-fill`,bufferLayout:t,isInstanced:!0}),o=new c.K(this.context.device,{...e,id:`${this.props.id}-wireframe`,bufferLayout:t,isInstanced:!0});return{fillModel:i,wireframeModel:o,models:[o,i]}}_updateGeometry({diskResolution:e,vertices:t,extruded:i,stroked:o}){let n=this.getGeometry(e,t,i||o);this.setState({fillVertexCount:n.attributes.POSITION.value.length/3});let s=this.state.fillModel,r=this.state.wireframeModel;s.setGeometry(n),s.setTopology("triangle-strip"),s.setIndexBuffer(null),r.setGeometry(n),r.setTopology("line-list")}draw({uniforms:e}){let{lineWidthUnits:t,lineWidthScale:i,lineWidthMinPixels:o,lineWidthMaxPixels:n,radiusUnits:s,elevationScale:a,extruded:l,filled:c,stroked:u,wireframe:d,offset:p,coverage:g,radius:f,angle:h}=this.props,v=this.state.fillModel,x=this.state.wireframeModel,{fillVertexCount:y,edgeDistance:m}=this.state,P={radius:f,angle:h/180*Math.PI,offset:p,extruded:l,stroked:u,coverage:g,elevationScale:a,edgeDistance:m,radiusUnits:r.p5[s],widthUnits:r.p5[t],widthScale:i,widthMinPixels:o,widthMaxPixels:n};l&&d&&(x.shaderInputs.setProps({column:{...P,isStroke:!0}}),x.draw(this.context.renderPass)),c&&(v.setVertexCount(y),v.shaderInputs.setProps({column:{...P,isStroke:!1}}),v.draw(this.context.renderPass)),!l&&u&&(v.setVertexCount(2*y/3),v.shaderInputs.setProps({column:{...P,isStroke:!0}}),v.draw(this.context.renderPass))}}P.layerName="ColumnLayer",P.defaultProps=m;let _=P},45877:(e,t,i)=>{i.d(t,{A:()=>b});var o=i(24125),n=i(85036),s=i(60738),r=i(48606),a=i(19188),l=i(8865),c=i(82940);let u={circle:{type:r.A,props:{filled:"filled",stroked:"stroked",lineWidthMaxPixels:"lineWidthMaxPixels",lineWidthMinPixels:"lineWidthMinPixels",lineWidthScale:"lineWidthScale",lineWidthUnits:"lineWidthUnits",pointRadiusMaxPixels:"radiusMaxPixels",pointRadiusMinPixels:"radiusMinPixels",pointRadiusScale:"radiusScale",pointRadiusUnits:"radiusUnits",pointAntialiasing:"antialiasing",pointBillboard:"billboard",getFillColor:"getFillColor",getLineColor:"getLineColor",getLineWidth:"getLineWidth",getPointRadius:"getRadius"}},icon:{type:s.A,props:{iconAtlas:"iconAtlas",iconMapping:"iconMapping",iconSizeMaxPixels:"sizeMaxPixels",iconSizeMinPixels:"sizeMinPixels",iconSizeScale:"sizeScale",iconSizeUnits:"sizeUnits",iconAlphaCutoff:"alphaCutoff",iconBillboard:"billboard",getIcon:"getIcon",getIconAngle:"getAngle",getIconColor:"getColor",getIconPixelOffset:"getPixelOffset",getIconSize:"getSize"}},text:{type:a.A,props:{textSizeMaxPixels:"sizeMaxPixels",textSizeMinPixels:"sizeMinPixels",textSizeScale:"sizeScale",textSizeUnits:"sizeUnits",textBackground:"background",textBackgroundPadding:"backgroundPadding",textFontFamily:"fontFamily",textFontWeight:"fontWeight",textLineHeight:"lineHeight",textMaxWidth:"maxWidth",textOutlineColor:"outlineColor",textOutlineWidth:"outlineWidth",textWordBreak:"wordBreak",textCharacterSet:"characterSet",textBillboard:"billboard",textFontSettings:"fontSettings",getText:"getText",getTextAngle:"getAngle",getTextColor:"getColor",getTextPixelOffset:"getPixelOffset",getTextSize:"getSize",getTextAnchor:"getTextAnchor",getTextAlignmentBaseline:"getAlignmentBaseline",getTextBackgroundColor:"getBackgroundColor",getTextBorderColor:"getBorderColor",getTextBorderWidth:"getBorderWidth"}}},d={type:l.A,props:{lineWidthUnits:"widthUnits",lineWidthScale:"widthScale",lineWidthMinPixels:"widthMinPixels",lineWidthMaxPixels:"widthMaxPixels",lineJointRounded:"jointRounded",lineCapRounded:"capRounded",lineMiterLimit:"miterLimit",lineBillboard:"billboard",getLineColor:"getColor",getLineWidth:"getWidth"}},p={type:c.A,props:{extruded:"extruded",filled:"filled",wireframe:"wireframe",elevationScale:"elevationScale",material:"material",_full3d:"_full3d",getElevation:"getElevation",getFillColor:"getFillColor",getLineColor:"getLineColor"}};function g({type:e,props:t}){let i={};for(let o in t)i[o]=e.defaultProps[t[o]];return i}function f(e,t){let{transitions:i,updateTriggers:o}=e.props,n={updateTriggers:{},transitions:i&&{getPosition:i.geometry}};for(let s in t){let r=t[s],a=e.props[s];s.startsWith("get")&&(a=e.getSubLayerAccessor(a),n.updateTriggers[r]=o[s],i&&(n.transitions[r]=i[s])),n[r]=a}return n}var h=i(77002);function v(e,t,i={}){let o={pointFeatures:[],lineFeatures:[],polygonFeatures:[],polygonOutlineFeatures:[]},{startRow:n=0,endRow:s=e.length}=i;for(let i=n;i<s;i++){let n=e[i],{geometry:s}=n;if(s){if("GeometryCollection"===s.type){h.A.assert(Array.isArray(s.geometries),"GeoJSON does not have geometries array");let{geometries:e}=s;for(let s=0;s<e.length;s++)x(e[s],o,t,n,i)}else x(s,o,t,n,i)}}return o}function x(e,t,i,o,n){let{type:s,coordinates:r}=e,{pointFeatures:a,lineFeatures:l,polygonFeatures:c,polygonOutlineFeatures:u}=t;if(!function(e,t){let i=y[e];for(h.A.assert(i,`Unknown GeoJSON type ${e}`);t&&--i>0;)t=t[0];return t&&Number.isFinite(t[0])}(s,r)){h.A.warn(`${s} coordinates are malformed`)();return}switch(s){case"Point":a.push(i({geometry:e},o,n));break;case"MultiPoint":r.forEach(e=>{a.push(i({geometry:{type:"Point",coordinates:e}},o,n))});break;case"LineString":l.push(i({geometry:e},o,n));break;case"MultiLineString":r.forEach(e=>{l.push(i({geometry:{type:"LineString",coordinates:e}},o,n))});break;case"Polygon":c.push(i({geometry:e},o,n)),r.forEach(e=>{u.push(i({geometry:{type:"LineString",coordinates:e}},o,n))});break;case"MultiPolygon":r.forEach(e=>{c.push(i({geometry:{type:"Polygon",coordinates:e}},o,n)),e.forEach(e=>{u.push(i({geometry:{type:"LineString",coordinates:e}},o,n))})})}}let y={Point:1,MultiPoint:2,LineString:2,MultiLineString:3,Polygon:3,MultiPolygon:4};function m(){return{points:{},lines:{},polygons:{},polygonsOutline:{}}}function P(e){return e.geometry.coordinates}let _=["points","linestrings","polygons"],C={...g(u.circle),...g(u.icon),...g(u.text),...g(d),...g(p),stroked:!0,filled:!0,extruded:!1,wireframe:!1,_full3d:!1,iconAtlas:{type:"object",value:null},iconMapping:{type:"object",value:{}},getIcon:{type:"accessor",value:e=>e.properties.icon},getText:{type:"accessor",value:e=>e.properties.text},pointType:"circle",getRadius:{deprecatedFor:"getPointRadius"}};class L extends o.A{initializeState(){this.state={layerProps:{},features:{},featuresDiff:{}}}updateState({props:e,changeFlags:t}){if(!t.dataChanged)return;let{data:i}=this.props,o=i&&"points"in i&&"polygons"in i&&"lines"in i;this.setState({binary:o}),o?this._updateStateBinary({props:e,changeFlags:t}):this._updateStateJSON({props:e,changeFlags:t})}_updateStateBinary({props:e,changeFlags:t}){let i=function(e,t){let i=m(),{points:o,lines:n,polygons:s}=e,r=function(e,t){let i={points:null,lines:null,polygons:null};for(let o in i){let n=e[o].globalFeatureIds.value;i[o]=new Uint8ClampedArray(4*n.length);let s=[];for(let e=0;e<n.length;e++)t(n[e],s),i[o][4*e+0]=s[0],i[o][4*e+1]=s[1],i[o][4*e+2]=s[2],i[o][4*e+3]=255}return i}(e,t);i.points.data={length:o.positions.value.length/o.positions.size,attributes:{...o.attributes,getPosition:o.positions,instancePickingColors:{size:4,value:r.points}},properties:o.properties,numericProps:o.numericProps,featureIds:o.featureIds},i.lines.data={length:n.pathIndices.value.length-1,startIndices:n.pathIndices.value,attributes:{...n.attributes,getPath:n.positions,instancePickingColors:{size:4,value:r.lines}},properties:n.properties,numericProps:n.numericProps,featureIds:n.featureIds},i.lines._pathType="open";let a=Array(s.positions.value.length/s.positions.size).fill(1);for(let e of s.primitivePolygonIndices.value)a[e-1]=0;return i.polygons.data={length:s.polygonIndices.value.length-1,startIndices:s.polygonIndices.value,attributes:{...s.attributes,getPolygon:s.positions,instanceVertexValid:{size:1,value:new Uint16Array(a)},pickingColors:{size:4,value:r.polygons}},properties:s.properties,numericProps:s.numericProps,featureIds:s.featureIds},i.polygons._normalize=!1,s.triangles&&(i.polygons.data.attributes.indices=s.triangles.value),i.polygonsOutline.data={length:s.primitivePolygonIndices.value.length-1,startIndices:s.primitivePolygonIndices.value,attributes:{...s.attributes,getPath:s.positions,instancePickingColors:{size:4,value:r.polygons}},properties:s.properties,numericProps:s.numericProps,featureIds:s.featureIds},i.polygonsOutline._pathType="open",i}(e.data,this.encodePickingColor);this.setState({layerProps:i})}_updateStateJSON({props:e,changeFlags:t}){let i=function(e){if(Array.isArray(e))return e;switch(h.A.assert(e.type,"GeoJSON does not have type"),e.type){case"Feature":return[e];case"FeatureCollection":return h.A.assert(Array.isArray(e.features),"GeoJSON does not have features array"),e.features;default:return[{geometry:e}]}}(e.data),o=this.getSubLayerRow.bind(this),s={},r={};if(Array.isArray(t.dataChanged)){let e=this.state.features;for(let t in e)s[t]=e[t].slice(),r[t]=[];for(let a of t.dataChanged){let t=v(i,o,a);for(let i in e)r[i].push((0,n.J)({data:s[i],getIndex:e=>e.__source.index,dataRange:a,replace:t[i]}))}}else s=v(i,o);let a=function(e,t){let i=m(),{pointFeatures:o,lineFeatures:n,polygonFeatures:s,polygonOutlineFeatures:r}=e;return i.points.data=o,i.points._dataDiff=t.pointFeatures&&(()=>t.pointFeatures),i.points.getPosition=P,i.lines.data=n,i.lines._dataDiff=t.lineFeatures&&(()=>t.lineFeatures),i.lines.getPath=P,i.polygons.data=s,i.polygons._dataDiff=t.polygonFeatures&&(()=>t.polygonFeatures),i.polygons.getPolygon=P,i.polygonsOutline.data=r,i.polygonsOutline._dataDiff=t.polygonOutlineFeatures&&(()=>t.polygonOutlineFeatures),i.polygonsOutline.getPath=P,i}(s,r);this.setState({features:s,featuresDiff:r,layerProps:a})}getPickingInfo(e){let t=super.getPickingInfo(e),{index:i,sourceLayer:o}=t;return t.featureType=_.find(e=>o.id.startsWith(`${this.id}-${e}-`)),i>=0&&o.id.startsWith(`${this.id}-points-text`)&&this.state.binary&&(t.index=this.props.data.points.globalFeatureIds.value[i]),t}_updateAutoHighlight(e){let t=`${this.id}-points-`,i="points"===e.featureType;for(let o of this.getSubLayers())o.id.startsWith(t)===i&&o.updateAutoHighlight(e)}_renderPolygonLayer(){let{extruded:e,wireframe:t}=this.props,{layerProps:i}=this.state,o="polygons-fill",n=this.shouldRenderSubLayer(o,i.polygons?.data)&&this.getSubLayerClass(o,p.type);if(n){let s=f(this,p.props),r=e&&t;return r||delete s.getLineColor,s.updateTriggers.lineColors=r,new n(s,this.getSubLayerProps({id:o,updateTriggers:s.updateTriggers}),i.polygons)}return null}_renderLineLayers(){let{extruded:e,stroked:t}=this.props,{layerProps:i}=this.state,o="polygons-stroke",n="linestrings",s=!e&&t&&this.shouldRenderSubLayer(o,i.polygonsOutline?.data)&&this.getSubLayerClass(o,d.type),r=this.shouldRenderSubLayer(n,i.lines?.data)&&this.getSubLayerClass(n,d.type);if(s||r){let e=f(this,d.props);return[s&&new s(e,this.getSubLayerProps({id:o,updateTriggers:e.updateTriggers}),i.polygonsOutline),r&&new r(e,this.getSubLayerProps({id:n,updateTriggers:e.updateTriggers}),i.lines)]}return null}_renderPointLayers(){let{pointType:e}=this.props,{layerProps:t,binary:i}=this.state,{highlightedObjectIndex:o}=this.props;!i&&Number.isFinite(o)&&(o=t.points.data.findIndex(e=>e.__source.index===o));let n=new Set(e.split("+")),s=[];for(let e of n){let n=`points-${e}`,r=u[e],a=r&&this.shouldRenderSubLayer(n,t.points?.data)&&this.getSubLayerClass(n,r.type);if(a){let l=f(this,r.props),c=t.points;if("text"===e&&i){let{instancePickingColors:e,...t}=c.data.attributes;c={...c,data:{...c.data,attributes:t}}}s.push(new a(l,this.getSubLayerProps({id:n,updateTriggers:l.updateTriggers,highlightedObjectIndex:o}),c))}}return s}renderLayers(){let{extruded:e}=this.props,t=this._renderPolygonLayer();return[!e&&t,this._renderLineLayers(),this._renderPointLayers(),e&&t]}getSubLayerAccessor(e){let{binary:t}=this.state;return t&&"function"==typeof e?(t,i)=>{let{data:o,index:n}=i;return e(function(e,t){if(!e)return null;let i="startIndices"in e?e.startIndices[t]:t,o=e.featureIds.value[i];return -1!==i?function(e,t,i){let o={properties:{...e.properties[t]}};for(let t in e.numericProps)o.properties[t]=e.numericProps[t].value[i];return o}(e,o,i):null}(o,n),i)}:super.getSubLayerAccessor(e)}}L.layerName="GeoJsonLayer",L.defaultProps=C;let b=L},60738:(e,t,i)=>{i.d(t,{A:()=>S});var o=i(98318),n=i(2854),s=i(65489),r=i(60303),a=i(77002),l=i(91538),c=i(88912);let u=`\
uniform iconUniforms {
  float sizeScale;
  vec2 iconsTextureDim;
  float sizeBasis;
  float sizeMinPixels;
  float sizeMaxPixels;
  bool billboard;
  highp int sizeUnits;
  float alphaCutoff;
} icon;
`,d={name:"icon",vs:u,fs:u,uniformTypes:{sizeScale:"f32",iconsTextureDim:"vec2<f32>",sizeBasis:"f32",sizeMinPixels:"f32",sizeMaxPixels:"f32",billboard:"f32",sizeUnits:"i32",alphaCutoff:"f32"}},p=`\
#version 300 es
#define SHADER_NAME icon-layer-vertex-shader
in vec2 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in float instanceSizes;
in float instanceAngles;
in vec4 instanceColors;
in vec3 instancePickingColors;
in vec4 instanceIconFrames;
in float instanceColorModes;
in vec2 instanceOffsets;
in vec2 instancePixelOffset;
out float vColorMode;
out vec4 vColor;
out vec2 vTextureCoords;
out vec2 uv;
vec2 rotate_by_angle(vec2 vertex, float angle) {
float angle_radian = angle * PI / 180.0;
float cos_angle = cos(angle_radian);
float sin_angle = sin(angle_radian);
mat2 rotationMatrix = mat2(cos_angle, -sin_angle, sin_angle, cos_angle);
return rotationMatrix * vertex;
}
void main(void) {
geometry.worldPosition = instancePositions;
geometry.uv = positions;
geometry.pickingColor = instancePickingColors;
uv = positions;
vec2 iconSize = instanceIconFrames.zw;
float sizePixels = clamp(
project_size_to_pixel(instanceSizes * icon.sizeScale, icon.sizeUnits),
icon.sizeMinPixels, icon.sizeMaxPixels
);
float iconConstraint = icon.sizeBasis == 0.0 ? iconSize.x : iconSize.y;
float instanceScale = iconConstraint == 0.0 ? 0.0 : sizePixels / iconConstraint;
vec2 pixelOffset = positions / 2.0 * iconSize + instanceOffsets;
pixelOffset = rotate_by_angle(pixelOffset, instanceAngles) * instanceScale;
pixelOffset += instancePixelOffset;
pixelOffset.y *= -1.0;
if (icon.billboard)  {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = vec3(pixelOffset, 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset_common = vec3(project_pixel_size(pixelOffset), 0.0);
DECKGL_FILTER_SIZE(offset_common, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset_common, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
vTextureCoords = mix(
instanceIconFrames.xy,
instanceIconFrames.xy + iconSize,
(positions.xy + 1.0) / 2.0
) / icon.iconsTextureDim;
vColor = instanceColors;
DECKGL_FILTER_COLOR(vColor, geometry);
vColorMode = instanceColorModes;
}
`,g=`\
#version 300 es
#define SHADER_NAME icon-layer-fragment-shader
precision highp float;
uniform sampler2D iconsTexture;
in float vColorMode;
in vec4 vColor;
in vec2 vTextureCoords;
in vec2 uv;
out vec4 fragColor;
void main(void) {
geometry.uv = uv;
vec4 texColor = texture(iconsTexture, vTextureCoords);
vec3 color = mix(texColor.rgb, vColor.rgb, vColorMode);
float a = texColor.a * layer.opacity * vColor.a;
if (a < icon.alphaCutoff) {
discard;
}
fragColor = vec4(color, a);
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`;var f=i(3101),h=i(98614);let v=()=>{},x={minFilter:"linear",mipmapFilter:"linear",magFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge"},y={x:0,y:0,width:0,height:0};function m(e){return e&&(e.id||e.url)}function P(e,t,i){for(let o=0;o<t.length;o++){let{icon:n,xOffset:s}=t[o];e[m(n)]={...n,x:s,y:i}}}class _{constructor(e,{onUpdate:t=v,onError:i=v}){this._loadOptions=null,this._texture=null,this._externalTexture=null,this._mapping={},this._samplerParameters=null,this._pendingCount=0,this._autoPacking=!1,this._xOffset=0,this._yOffset=0,this._rowHeight=0,this._buffer=4,this._canvasWidth=1024,this._canvasHeight=0,this._canvas=null,this.device=e,this.onUpdate=t,this.onError=i}finalize(){this._texture?.delete()}getTexture(){return this._texture||this._externalTexture}getIconMapping(e){let t=this._autoPacking?m(e):e;return this._mapping[t]||y}setProps({loadOptions:e,autoPacking:t,iconAtlas:i,iconMapping:o,textureParameters:n}){e&&(this._loadOptions=e),void 0!==t&&(this._autoPacking=t),o&&(this._mapping=o),i&&(this._texture?.delete(),this._texture=null,this._externalTexture=i),n&&(this._samplerParameters=n)}get isLoaded(){return 0===this._pendingCount}packIcons(e,t){if(!this._autoPacking||"undefined"==typeof document)return;let i=Object.values(function(e,t,i){if(!e||!t)return null;i=i||{};let o={},{iterable:n,objectInfo:s}=(0,h.X)(e);for(let e of n){s.index++;let n=t(e,s),r=m(n);if(!n)throw Error("Icon is missing.");if(!n.url)throw Error("Icon url is missing.");o[r]||i[r]&&n.url===i[r].url||(o[r]={...n,source:e,sourceIndex:s.index})}return o}(e,t,this._mapping)||{});if(i.length>0){let{mapping:e,xOffset:t,yOffset:o,rowHeight:n,canvasHeight:s}=function({icons:e,buffer:t,mapping:i={},xOffset:o=0,yOffset:n=0,rowHeight:s=0,canvasWidth:r}){let a=[];for(let l=0;l<e.length;l++){let c=e[l];if(!i[m(c)]){let{height:e,width:l}=c;o+l+t>r&&(P(i,a,n),o=0,n=s+n+t,s=0,a=[]),a.push({icon:c,xOffset:o}),o=o+l+t,s=Math.max(s,e)}}return a.length>0&&P(i,a,n),{mapping:i,rowHeight:s,xOffset:o,yOffset:n,canvasWidth:r,canvasHeight:Math.pow(2,Math.ceil(Math.log2(s+n+t)))}}({icons:i,buffer:this._buffer,canvasWidth:this._canvasWidth,mapping:this._mapping,rowHeight:this._rowHeight,xOffset:this._xOffset,yOffset:this._yOffset});this._rowHeight=n,this._mapping=e,this._xOffset=t,this._yOffset=o,this._canvasHeight=s,this._texture||(this._texture=this.device.createTexture({format:"rgba8unorm",data:null,width:this._canvasWidth,height:this._canvasHeight,sampler:this._samplerParameters||x,mipLevels:this.device.getMipLevelCount(this._canvasWidth,this._canvasHeight)})),this._texture.height!==this._canvasHeight&&(this._texture=function(e,t,i,o){let{width:n,height:s,device:r}=e,a=r.createTexture({format:"rgba8unorm",width:t,height:i,sampler:o,mipLevels:r.getMipLevelCount(t,i)}),l=r.createCommandEncoder();return l.copyTextureToTexture({sourceTexture:e,destinationTexture:a,width:n,height:s}),l.finish(),a.generateMipmapsWebGL(),e.destroy(),a}(this._texture,this._canvasWidth,this._canvasHeight,this._samplerParameters||x)),this.onUpdate(!0),this._canvas=this._canvas||document.createElement("canvas"),this._loadIcons(i)}}_loadIcons(e){let t=this._canvas.getContext("2d",{willReadFrequently:!0});for(let i of e)this._pendingCount++,(0,f.H)(i.url,this._loadOptions).then(e=>{let o=m(i),n=this._mapping[o],{x:s,y:r,width:a,height:l}=n,{image:c,width:u,height:d}=function(e,t,i,o){let n=Math.min(i/t.width,o/t.height),s=Math.floor(t.width*n),r=Math.floor(t.height*n);return 1===n?{image:t,width:s,height:r}:(e.canvas.height=r,e.canvas.width=s,e.clearRect(0,0,s,r),e.drawImage(t,0,0,t.width,t.height,0,0,s,r),{image:e.canvas,width:s,height:r})}(t,e,a,l),p=s+(a-u)/2,g=r+(l-d)/2;this._texture?.copyExternalImage({image:c,x:p,y:g,width:u,height:d}),n.x=p,n.y=g,n.width=u,n.height=d,this._texture?.generateMipmapsWebGL(),this.onUpdate(u!==a||d!==l)}).catch(e=>{this.onError({url:i.url,source:i.source,sourceIndex:i.sourceIndex,loadOptions:this._loadOptions,error:e})}).finally(()=>{this._pendingCount--})}}let C=[0,0,0,255],L={iconAtlas:{type:"image",value:null,async:!0},iconMapping:{type:"object",value:{},async:!0},sizeScale:{type:"number",value:1,min:0},billboard:!0,sizeUnits:"pixels",sizeBasis:"height",sizeMinPixels:{type:"number",min:0,value:0},sizeMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},alphaCutoff:{type:"number",value:.05,min:0,max:1},getPosition:{type:"accessor",value:e=>e.position},getIcon:{type:"accessor",value:e=>e.icon},getColor:{type:"accessor",value:C},getSize:{type:"accessor",value:1},getAngle:{type:"accessor",value:0},getPixelOffset:{type:"accessor",value:[0,0]},onIconError:{type:"function",value:null,optional:!0},textureParameters:{type:"object",ignore:!0,value:null}};class b extends o.A{getShaders(){return super.getShaders({vs:p,fs:g,modules:[n.A,s.A,d]})}initializeState(){this.state={iconManager:new _(this.context.device,{onUpdate:this._onUpdate.bind(this),onError:this._onError.bind(this)})},this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceSizes:{size:1,transition:!0,accessor:"getSize",defaultValue:1},instanceOffsets:{size:2,accessor:"getIcon",transform:this.getInstanceOffset},instanceIconFrames:{size:4,accessor:"getIcon",transform:this.getInstanceIconFrame},instanceColorModes:{size:1,type:"uint8",accessor:"getIcon",transform:this.getInstanceColorMode},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getColor",defaultValue:C},instanceAngles:{size:1,transition:!0,accessor:"getAngle"},instancePixelOffset:{size:2,transition:!0,accessor:"getPixelOffset"}})}updateState(e){super.updateState(e);let{props:t,oldProps:i,changeFlags:o}=e,n=this.getAttributeManager(),{iconAtlas:s,iconMapping:r,data:a,getIcon:l,textureParameters:c}=t,{iconManager:u}=this.state;if("string"==typeof s)return;let d=s||this.internalState.isAsyncPropLoading("iconAtlas");u.setProps({loadOptions:t.loadOptions,autoPacking:!d,iconAtlas:s,iconMapping:d?r:null,textureParameters:c}),d?i.iconMapping!==t.iconMapping&&n.invalidate("getIcon"):(o.dataChanged||o.updateTriggersChanged&&(o.updateTriggersChanged.all||o.updateTriggersChanged.getIcon))&&u.packIcons(a,l),o.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),n.invalidateAll())}get isLoaded(){return super.isLoaded&&this.state.iconManager.isLoaded}finalizeState(e){super.finalizeState(e),this.state.iconManager.finalize()}draw({uniforms:e}){let{sizeScale:t,sizeBasis:i,sizeMinPixels:o,sizeMaxPixels:n,sizeUnits:s,billboard:a,alphaCutoff:l}=this.props,{iconManager:c}=this.state,u=c.getTexture();if(u){let e=this.state.model,c={iconsTexture:u,iconsTextureDim:[u.width,u.height],sizeUnits:r.p5[s],sizeScale:t,sizeBasis:"height"===i?1:0,sizeMinPixels:o,sizeMaxPixels:n,billboard:a,alphaCutoff:l};e.shaderInputs.setProps({icon:c}),e.draw(this.context.renderPass)}}_getModel(){return new l.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new c.V({topology:"triangle-strip",attributes:{positions:{size:2,value:new Float32Array([-1,-1,1,-1,-1,1,1,1])}}}),isInstanced:!0})}_onUpdate(e){e?(this.getAttributeManager()?.invalidate("getIcon"),this.setNeedsUpdate()):this.setNeedsRedraw()}_onError(e){let t=this.getCurrentLayer()?.props.onIconError;t?t(e):a.A.error(e.error.message)()}getInstanceOffset(e){let{width:t,height:i,anchorX:o=t/2,anchorY:n=i/2}=this.state.iconManager.getIconMapping(e);return[t/2-o,i/2-n]}getInstanceColorMode(e){return this.state.iconManager.getIconMapping(e).mask?1:0}getInstanceIconFrame(e){let{x:t,y:i,width:o,height:n}=this.state.iconManager.getIconMapping(e);return[t,i,o,n]}}b.defaultProps=L,b.layerName="IconLayer";let S=b},8865:(e,t,i)=>{i.d(t,{A:()=>_});var o=i(98318),n=i(2854),s=i(65489),r=i(60303),a=i(88912),l=i(91538),c=i(53028),u=i(95952);class d extends c.A{constructor(e){super({...e,attributes:{positions:{size:3,padding:18,initialize:!0,type:e.fp64?Float64Array:Float32Array},segmentTypes:{size:1,type:Uint8ClampedArray}}})}get(e){return this.attributes[e]}getGeometryFromBuffer(e){return this.normalize?super.getGeometryFromBuffer(e):null}normalizeGeometry(e){return this.normalize?function(e,t,i,o){let n;if(Array.isArray(e[0])){n=Array(e.length*t);for(let i=0;i<e.length;i++)for(let o=0;o<t;o++)n[i*t+o]=e[i][o]||0}else n=e;return i?(0,u.Mk)(n,{size:t,gridResolution:i}):o?(0,u.Iy)(n,{size:t}):n}(e,this.positionSize,this.opts.resolution,this.opts.wrapLongitude):e}getGeometrySize(e){if(p(e)){let t=0;for(let i of e)t+=this.getGeometrySize(i);return t}let t=this.getPathLength(e);return t<2?0:this.isClosed(e)?t<3?0:t+2:t}updateGeometryAttributes(e,t){if(0!==t.geometrySize){if(e&&p(e))for(let i of e){let e=this.getGeometrySize(i);t.geometrySize=e,this.updateGeometryAttributes(i,t),t.vertexStart+=e}else this._updateSegmentTypes(e,t),this._updatePositions(e,t)}}_updateSegmentTypes(e,t){let i=this.attributes.segmentTypes,o=!!e&&this.isClosed(e),{vertexStart:n,geometrySize:s}=t;i.fill(0,n,n+s),o?(i[n]=4,i[n+s-2]=4):(i[n]+=1,i[n+s-2]+=2),i[n+s-1]=4}_updatePositions(e,t){let{positions:i}=this.attributes;if(!i||!e)return;let{vertexStart:o,geometrySize:n}=t,s=[,,,];for(let t=o,r=0;r<n;t++,r++)this.getPointOnPath(e,r,s),i[3*t]=s[0],i[3*t+1]=s[1],i[3*t+2]=s[2]}getPathLength(e){return e.length/this.positionSize}getPointOnPath(e,t,i=[]){let{positionSize:o}=this;t*o>=e.length&&(t+=1-e.length/o);let n=t*o;return i[0]=e[n],i[1]=e[n+1],i[2]=3===o&&e[n+2]||0,i}isClosed(e){if(!this.normalize)return!!this.opts.loop;let{positionSize:t}=this,i=e.length-t;return e[0]===e[i]&&e[1]===e[i+1]&&(2===t||e[2]===e[i+2])}}function p(e){return Array.isArray(e[0])}let g=`\
uniform pathUniforms {
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  float jointType;
  float capType;
  float miterLimit;
  bool billboard;
  highp int widthUnits;
} path;
`,f={name:"path",vs:g,fs:g,uniformTypes:{widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",jointType:"f32",capType:"f32",miterLimit:"f32",billboard:"f32",widthUnits:"i32"}},h=`\
#version 300 es
#define SHADER_NAME path-layer-vertex-shader
in vec2 positions;
in float instanceTypes;
in vec3 instanceStartPositions;
in vec3 instanceEndPositions;
in vec3 instanceLeftPositions;
in vec3 instanceRightPositions;
in vec3 instanceLeftPositions64Low;
in vec3 instanceStartPositions64Low;
in vec3 instanceEndPositions64Low;
in vec3 instanceRightPositions64Low;
in float instanceStrokeWidths;
in vec4 instanceColors;
in vec3 instancePickingColors;
uniform float opacity;
out vec4 vColor;
out vec2 vCornerOffset;
out float vMiterLength;
out vec2 vPathPosition;
out float vPathLength;
out float vJointType;
const float EPSILON = 0.001;
const vec3 ZERO_OFFSET = vec3(0.0);
float flipIfTrue(bool flag) {
return -(float(flag) * 2. - 1.);
}
vec3 getLineJoinOffset(
vec3 prevPoint, vec3 currPoint, vec3 nextPoint,
vec2 width
) {
bool isEnd = positions.x > 0.0;
float sideOfPath = positions.y;
float isJoint = float(sideOfPath == 0.0);
vec3 deltaA3 = (currPoint - prevPoint);
vec3 deltaB3 = (nextPoint - currPoint);
mat3 rotationMatrix;
bool needsRotation = !path.billboard && project_needs_rotation(currPoint, rotationMatrix);
if (needsRotation) {
deltaA3 = deltaA3 * rotationMatrix;
deltaB3 = deltaB3 * rotationMatrix;
}
vec2 deltaA = deltaA3.xy / width;
vec2 deltaB = deltaB3.xy / width;
float lenA = length(deltaA);
float lenB = length(deltaB);
vec2 dirA = lenA > 0. ? normalize(deltaA) : vec2(0.0, 0.0);
vec2 dirB = lenB > 0. ? normalize(deltaB) : vec2(0.0, 0.0);
vec2 perpA = vec2(-dirA.y, dirA.x);
vec2 perpB = vec2(-dirB.y, dirB.x);
vec2 tangent = dirA + dirB;
tangent = length(tangent) > 0. ? normalize(tangent) : perpA;
vec2 miterVec = vec2(-tangent.y, tangent.x);
vec2 dir = isEnd ? dirA : dirB;
vec2 perp = isEnd ? perpA : perpB;
float L = isEnd ? lenA : lenB;
float sinHalfA = abs(dot(miterVec, perp));
float cosHalfA = abs(dot(dirA, miterVec));
float turnDirection = flipIfTrue(dirA.x * dirB.y >= dirA.y * dirB.x);
float cornerPosition = sideOfPath * turnDirection;
float miterSize = 1.0 / max(sinHalfA, EPSILON);
miterSize = mix(
min(miterSize, max(lenA, lenB) / max(cosHalfA, EPSILON)),
miterSize,
step(0.0, cornerPosition)
);
vec2 offsetVec = mix(miterVec * miterSize, perp, step(0.5, cornerPosition))
* (sideOfPath + isJoint * turnDirection);
bool isStartCap = lenA == 0.0 || (!isEnd && (instanceTypes == 1.0 || instanceTypes == 3.0));
bool isEndCap = lenB == 0.0 || (isEnd && (instanceTypes == 2.0 || instanceTypes == 3.0));
bool isCap = isStartCap || isEndCap;
if (isCap) {
offsetVec = mix(perp * sideOfPath, dir * path.capType * 4.0 * flipIfTrue(isStartCap), isJoint);
vJointType = path.capType;
} else {
vJointType = path.jointType;
}
vPathLength = L;
vCornerOffset = offsetVec;
vMiterLength = dot(vCornerOffset, miterVec * turnDirection);
vMiterLength = isCap ? isJoint : vMiterLength;
vec2 offsetFromStartOfPath = vCornerOffset + deltaA * float(isEnd);
vPathPosition = vec2(
dot(offsetFromStartOfPath, perp),
dot(offsetFromStartOfPath, dir)
);
geometry.uv = vPathPosition;
float isValid = step(instanceTypes, 3.5);
vec3 offset = vec3(offsetVec * width * isValid, 0.0);
if (needsRotation) {
offset = rotationMatrix * offset;
}
return offset;
}
void clipLine(inout vec4 position, vec4 refPosition) {
if (position.w < EPSILON) {
float r = (EPSILON - refPosition.w) / (position.w - refPosition.w);
position = refPosition + (position - refPosition) * r;
}
}
void main() {
geometry.pickingColor = instancePickingColors;
vColor = vec4(instanceColors.rgb, instanceColors.a * layer.opacity);
float isEnd = positions.x;
vec3 prevPosition = mix(instanceLeftPositions, instanceStartPositions, isEnd);
vec3 prevPosition64Low = mix(instanceLeftPositions64Low, instanceStartPositions64Low, isEnd);
vec3 currPosition = mix(instanceStartPositions, instanceEndPositions, isEnd);
vec3 currPosition64Low = mix(instanceStartPositions64Low, instanceEndPositions64Low, isEnd);
vec3 nextPosition = mix(instanceEndPositions, instanceRightPositions, isEnd);
vec3 nextPosition64Low = mix(instanceEndPositions64Low, instanceRightPositions64Low, isEnd);
geometry.worldPosition = currPosition;
vec2 widthPixels = vec2(clamp(
project_size_to_pixel(instanceStrokeWidths * path.widthScale, path.widthUnits),
path.widthMinPixels, path.widthMaxPixels) / 2.0);
vec3 width;
if (path.billboard) {
vec4 prevPositionScreen = project_position_to_clipspace(prevPosition, prevPosition64Low, ZERO_OFFSET);
vec4 currPositionScreen = project_position_to_clipspace(currPosition, currPosition64Low, ZERO_OFFSET, geometry.position);
vec4 nextPositionScreen = project_position_to_clipspace(nextPosition, nextPosition64Low, ZERO_OFFSET);
clipLine(prevPositionScreen, currPositionScreen);
clipLine(nextPositionScreen, currPositionScreen);
clipLine(currPositionScreen, mix(nextPositionScreen, prevPositionScreen, isEnd));
width = vec3(widthPixels, 0.0);
DECKGL_FILTER_SIZE(width, geometry);
vec3 offset = getLineJoinOffset(
prevPositionScreen.xyz / prevPositionScreen.w,
currPositionScreen.xyz / currPositionScreen.w,
nextPositionScreen.xyz / nextPositionScreen.w,
project_pixel_size_to_clipspace(width.xy)
);
DECKGL_FILTER_GL_POSITION(currPositionScreen, geometry);
gl_Position = vec4(currPositionScreen.xyz + offset * currPositionScreen.w, currPositionScreen.w);
} else {
prevPosition = project_position(prevPosition, prevPosition64Low);
currPosition = project_position(currPosition, currPosition64Low);
nextPosition = project_position(nextPosition, nextPosition64Low);
width = vec3(project_pixel_size(widthPixels), 0.0);
DECKGL_FILTER_SIZE(width, geometry);
vec3 offset = getLineJoinOffset(prevPosition, currPosition, nextPosition, width.xy);
geometry.position = vec4(currPosition + offset, 1.0);
gl_Position = project_common_position_to_clipspace(geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,v=`\
#version 300 es
#define SHADER_NAME path-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 vCornerOffset;
in float vMiterLength;
in vec2 vPathPosition;
in float vPathLength;
in float vJointType;
out vec4 fragColor;
void main(void) {
geometry.uv = vPathPosition;
if (vPathPosition.y < 0.0 || vPathPosition.y > vPathLength) {
if (vJointType > 0.5 && length(vCornerOffset) > 1.0) {
discard;
}
if (vJointType < 0.5 && vMiterLength > path.miterLimit + 1.0) {
discard;
}
}
fragColor = vColor;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,x=[0,0,0,255],y={widthUnits:"meters",widthScale:{type:"number",min:0,value:1},widthMinPixels:{type:"number",min:0,value:0},widthMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},jointRounded:!1,capRounded:!1,miterLimit:{type:"number",min:0,value:4},billboard:!1,_pathType:null,getPath:{type:"accessor",value:e=>e.path},getColor:{type:"accessor",value:x},getWidth:{type:"accessor",value:1},rounded:{deprecatedFor:["jointRounded","capRounded"]}},m={enter:(e,t)=>t.length?t.subarray(t.length-e.length):e};class P extends o.A{getShaders(){return super.getShaders({vs:h,fs:v,modules:[n.A,s.A,f]})}get wrapLongitude(){return!1}getBounds(){return this.getAttributeManager()?.getBounds(["vertexPositions"])}initializeState(){this.getAttributeManager().addInstanced({vertexPositions:{size:3,vertexOffset:1,type:"float64",fp64:this.use64bitPositions(),transition:m,accessor:"getPath",update:this.calculatePositions,noAlloc:!0,shaderAttributes:{instanceLeftPositions:{vertexOffset:0},instanceStartPositions:{vertexOffset:1},instanceEndPositions:{vertexOffset:2},instanceRightPositions:{vertexOffset:3}}},instanceTypes:{size:1,type:"uint8",update:this.calculateSegmentTypes,noAlloc:!0},instanceStrokeWidths:{size:1,accessor:"getWidth",transition:m,defaultValue:1},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",accessor:"getColor",transition:m,defaultValue:x},instancePickingColors:{size:4,type:"uint8",accessor:(e,{index:t,target:i})=>this.encodePickingColor(e&&e.__source?e.__source.index:t,i)}}),this.setState({pathTesselator:new d({fp64:this.use64bitPositions()})})}updateState(e){super.updateState(e);let{props:t,changeFlags:i}=e,o=this.getAttributeManager();if(i.dataChanged||i.updateTriggersChanged&&(i.updateTriggersChanged.all||i.updateTriggersChanged.getPath)){let{pathTesselator:e}=this.state,n=t.data.attributes||{};e.updateGeometry({data:t.data,geometryBuffer:n.getPath,buffers:n,normalize:!t._pathType,loop:"loop"===t._pathType,getGeometry:t.getPath,positionFormat:t.positionFormat,wrapLongitude:t.wrapLongitude,resolution:this.context.viewport.resolution,dataChanged:i.dataChanged}),this.setState({numInstances:e.instanceCount,startIndices:e.vertexStarts}),i.dataChanged||o.invalidateAll()}i.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),o.invalidateAll())}getPickingInfo(e){let t=super.getPickingInfo(e),{index:i}=t,o=this.props.data;return o[0]&&o[0].__source&&(t.object=o.find(e=>e.__source.index===i)),t}disablePickingIndex(e){let t=this.props.data;if(t[0]&&t[0].__source)for(let i=0;i<t.length;i++)t[i].__source.index===e&&this._disablePickingIndex(i);else super.disablePickingIndex(e)}draw({uniforms:e}){let{jointRounded:t,capRounded:i,billboard:o,miterLimit:n,widthUnits:s,widthScale:a,widthMinPixels:l,widthMaxPixels:c}=this.props,u=this.state.model,d={jointType:Number(t),capType:Number(i),billboard:o,widthUnits:r.p5[s],widthScale:a,miterLimit:n,widthMinPixels:l,widthMaxPixels:c};u.shaderInputs.setProps({path:d}),u.draw(this.context.renderPass)}_getModel(){return new l.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new a.V({topology:"triangle-list",attributes:{indices:new Uint16Array([0,1,2,1,4,2,1,3,4,3,5,4]),positions:{value:new Float32Array([0,0,0,-1,0,1,1,-1,1,1,1,0]),size:2}}}),isInstanced:!0})}calculatePositions(e){let{pathTesselator:t}=this.state;e.startIndices=t.vertexStarts,e.value=t.get("positions")}calculateSegmentTypes(e){let{pathTesselator:t}=this.state;e.startIndices=t.vertexStarts,e.value=t.get("segmentTypes")}}P.defaultProps=y,P.layerName="PathLayer";let _=P},27718:(e,t,i)=>{i.d(t,{A:()=>m});var o=i(98318),n=i(2854),s=i(95086),r=i(65489),a=i(60303),l=i(91538),c=i(88912),u=i(75817);let d=`\
uniform pointCloudUniforms {
  float radiusPixels;
  highp int sizeUnits;
} pointCloud;
`,p={name:"pointCloud",source:`\
struct PointCloudUniforms {
  radiusPixels: f32,
  sizeUnits: i32,
};

@group(0) @binding(3)
var<uniform> pointCloud: PointCloudUniforms;
`,vs:d,fs:d,uniformTypes:{radiusPixels:"f32",sizeUnits:"i32"}},g=`\
#version 300 es
#define SHADER_NAME point-cloud-layer-vertex-shader
in vec3 positions;
in vec3 instanceNormals;
in vec4 instanceColors;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in vec3 instancePickingColors;
out vec4 vColor;
out vec2 unitPosition;
void main(void) {
geometry.worldPosition = instancePositions;
geometry.normal = project_normal(instanceNormals);
unitPosition = positions.xy;
geometry.uv = unitPosition;
geometry.pickingColor = instancePickingColors;
vec3 offset = vec3(positions.xy * project_size_to_pixel(pointCloud.radiusPixels, pointCloud.sizeUnits), 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
vec3 lightColor = lighting_getLightColor(instanceColors.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);
vColor = vec4(lightColor, instanceColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,f=`\
#version 300 es
#define SHADER_NAME point-cloud-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 unitPosition;
out vec4 fragColor;
void main(void) {
geometry.uv = unitPosition.xy;
float distToCenter = length(unitPosition);
if (distToCenter > 1.0) {
discard;
}
fragColor = vColor;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,h=`\
struct ConstantAttributes {
  instanceNormals: vec3<f32>,
  instanceColors: vec4<f32>,
  instancePositions: vec3<f32>,
  instancePositions64Low: vec3<f32>,
  instancePickingColors: vec3<f32>
};

const constants = ConstantAttributes(
  vec3<f32>(1.0, 0.0, 0.0),
  vec4<f32>(0.0, 0.0, 0.0, 1.0),
  vec3<f32>(0.0),
  vec3<f32>(0.0),
  vec3<f32>(0.0)
);

struct Attributes {
  @builtin(instance_index) instanceIndex : u32,
  @builtin(vertex_index) vertexIndex : u32,
  @location(0) positions: vec3<f32>,
  @location(1) instancePositions: vec3<f32>,
  @location(2) instancePositions64Low: vec3<f32>,
  @location(3) instanceNormals: vec3<f32>,
  @location(4) instanceColors: vec4<f32>,
  @location(5) instancePickingColors: vec3<f32>
};

struct Varyings {
  @builtin(position) position: vec4<f32>,
  @location(0) vColor: vec4<f32>,
  @location(1) unitPosition: vec2<f32>,
};

@vertex
fn vertexMain(attributes: Attributes) -> Varyings {
  var varyings: Varyings;
  
  // var geometry: Geometry;
  // geometry.worldPosition = instancePositions;
  // geometry.normal = project_normal(instanceNormals);

  // position on the containing square in [-1, 1] space
  varyings.unitPosition = attributes.positions.xy;
  geometry.uv = varyings.unitPosition;
  geometry.pickingColor = attributes.instancePickingColors;

  // Find the center of the point and add the current vertex
  let offset = vec3<f32>(attributes.positions.xy * project_unit_size_to_pixel(pointCloud.radiusPixels, pointCloud.sizeUnits), 0.0);
  // DECKGL_FILTER_SIZE(offset, geometry);

  varyings.position = project_position_to_clipspace(attributes.instancePositions, attributes.instancePositions64Low, vec3<f32>(0.0)); // TODO , geometry.position);
  // DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
  let clipPixels = project_pixel_size_to_clipspace(offset.xy);
  varyings.position.x += clipPixels.x;
  varyings.position.y += clipPixels.y;

  // Apply lighting
  let lightColor = lighting_getLightColor2(attributes.instanceColors.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);

  // Apply opacity to instance color, or return instance picking color
  varyings.vColor = vec4(lightColor, attributes.instanceColors.a * color.opacity);
  // DECKGL_FILTER_COLOR(vColor, geometry);

  return varyings;
}

@fragment
fn fragmentMain(varyings: Varyings) -> @location(0) vec4<f32> {
  // var geometry: Geometry;
  // geometry.uv = unitPosition.xy;

  let distToCenter = length(varyings.unitPosition);
  if (distToCenter > 1.0) {
    discard;
  }

  var fragColor: vec4<f32>;

  fragColor = varyings.vColor;
  // DECKGL_FILTER_COLOR(fragColor, geometry);

  // Apply premultiplied alpha as required by transparent canvas
  fragColor = deckgl_premultiplied_alpha(fragColor);

  return fragColor;
}
`,v=[0,0,0,255],x=[0,0,1];class y extends o.A{getShaders(){return super.getShaders({vs:g,fs:f,source:h,modules:[n.A,s.A,u.J,r.A,p]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceNormals:{size:3,transition:!0,accessor:"getNormal",defaultValue:x},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getColor",defaultValue:v}})}updateState(e){let{changeFlags:t,props:i}=e;super.updateState(e),t.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll()),t.dataChanged&&function(e){let{header:t,attributes:i}=e;if(t&&i&&(e.length=t.vertexCount,i.POSITION&&(i.instancePositions=i.POSITION),i.NORMAL&&(i.instanceNormals=i.NORMAL),i.COLOR_0)){let{size:e,value:t}=i.COLOR_0;i.instanceColors={size:e,type:"unorm8",value:t}}}(i.data)}draw({uniforms:e}){let{pointSize:t,sizeUnits:i}=this.props,o=this.state.model,n={sizeUnits:a.p5[i],radiusPixels:t};o.shaderInputs.setProps({pointCloud:n}),"webgpu"===this.context.device.type&&(o.instanceCount=this.props.data.length),o.draw(this.context.renderPass)}_getModel(){let e="webgpu"===this.context.device.type?{depthWriteEnabled:!0,depthCompare:"less-equal"}:void 0,t=[];for(let e=0;e<3;e++){let i=e/3*Math.PI*2;t.push(2*Math.cos(i),2*Math.sin(i),0)}return new l.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new c.V({topology:"triangle-list",attributes:{positions:new Float32Array(t)}}),parameters:e,isInstanced:!0})}}y.layerName="PointCloudLayer",y.defaultProps={sizeUnits:"pixels",pointSize:{type:"number",min:0,value:10},getPosition:{type:"accessor",value:e=>e.position},getNormal:{type:"accessor",value:x},getColor:{type:"accessor",value:v},material:!0,radiusPixels:{deprecatedFor:"pointSize"}};let m=y},65918:(e,t,i)=>{i.d(t,{A:()=>g});var o=i(24125),n=i(77002),s=i(98614),r=i(82940),a=i(8865),l=i(55596),c=i(85036);let u=[0,0,0,255],d={stroked:!0,filled:!0,extruded:!1,elevationScale:1,wireframe:!1,_normalize:!0,_windingOrder:"CW",lineWidthUnits:"meters",lineWidthScale:1,lineWidthMinPixels:0,lineWidthMaxPixels:Number.MAX_SAFE_INTEGER,lineJointRounded:!1,lineMiterLimit:4,getPolygon:{type:"accessor",value:e=>e.polygon},getFillColor:{type:"accessor",value:[0,0,0,255]},getLineColor:{type:"accessor",value:u},getLineWidth:{type:"accessor",value:1},getElevation:{type:"accessor",value:1e3},material:!0};class p extends o.A{initializeState(){this.state={paths:[],pathsDiff:null},this.props.getLineDashArray&&n.A.removed("getLineDashArray","PathStyleExtension")()}updateState({changeFlags:e}){let t=e.dataChanged||e.updateTriggersChanged&&(e.updateTriggersChanged.all||e.updateTriggersChanged.getPolygon);if(t&&Array.isArray(e.dataChanged)){let t=this.state.paths.slice(),i=e.dataChanged.map(e=>(0,c.J)({data:t,getIndex:e=>e.__source.index,dataRange:e,replace:this._getPaths(e)}));this.setState({paths:t,pathsDiff:i})}else t&&this.setState({paths:this._getPaths(),pathsDiff:null})}_getPaths(e={}){let{data:t,getPolygon:i,positionFormat:o,_normalize:n}=this.props,r=[],a="XY"===o?2:3,{startRow:c,endRow:u}=e,{iterable:d,objectInfo:p}=(0,s.X)(t,c,u);for(let e of d){p.index++;let t=i(e,p);n&&(t=l.S8(t,a));let{holeIndices:o}=t,s=t.positions||t;if(o)for(let t=0;t<=o.length;t++){let i=s.slice(o[t-1]||0,o[t]||s.length);r.push(this.getSubLayerRow({path:i},e,p.index))}else r.push(this.getSubLayerRow({path:s},e,p.index))}return r}renderLayers(){let{data:e,_dataDiff:t,stroked:i,filled:o,extruded:n,wireframe:s,_normalize:l,_windingOrder:c,elevationScale:d,transitions:p,positionFormat:g}=this.props,{lineWidthUnits:f,lineWidthScale:h,lineWidthMinPixels:v,lineWidthMaxPixels:x,lineJointRounded:y,lineMiterLimit:m,lineDashJustified:P}=this.props,{getFillColor:_,getLineColor:C,getLineWidth:L,getLineDashArray:b,getElevation:S,getPolygon:A,updateTriggers:w,material:I}=this.props,{paths:M,pathsDiff:z}=this.state,E=this.getSubLayerClass("fill",r.A),T=this.getSubLayerClass("stroke",a.A),R=this.shouldRenderSubLayer("fill",M)&&new E({_dataDiff:t,extruded:n,elevationScale:d,filled:o,wireframe:s,_normalize:l,_windingOrder:c,getElevation:S,getFillColor:_,getLineColor:n&&s?C:u,material:I,transitions:p},this.getSubLayerProps({id:"fill",updateTriggers:w&&{getPolygon:w.getPolygon,getElevation:w.getElevation,getFillColor:w.getFillColor,lineColors:n&&s,getLineColor:w.getLineColor}}),{data:e,positionFormat:g,getPolygon:A}),O=!n&&i&&this.shouldRenderSubLayer("stroke",M)&&new T({_dataDiff:z&&(()=>z),widthUnits:f,widthScale:h,widthMinPixels:v,widthMaxPixels:x,jointRounded:y,miterLimit:m,dashJustified:P,_pathType:"loop",transitions:p&&{getWidth:p.getLineWidth,getColor:p.getLineColor,getPath:p.getPolygon},getColor:this.getSubLayerAccessor(C),getWidth:this.getSubLayerAccessor(L),getDashArray:this.getSubLayerAccessor(b)},this.getSubLayerProps({id:"stroke",updateTriggers:w&&{getWidth:w.getLineWidth,getColor:w.getLineColor,getDashArray:w.getLineDashArray}}),{data:M,positionFormat:g,getPath:e=>e.path});return[!n&&R,O,n&&R]}}p.layerName="PolygonLayer",p.defaultProps=d;let g=p},48606:(e,t,i)=>{i.d(t,{A:()=>y});var o=i(98318),n=i(2854),s=i(95086),r=i(65489),a=i(60303),l=i(91538),c=i(88912);let u=`\
uniform scatterplotUniforms {
  float radiusScale;
  float radiusMinPixels;
  float radiusMaxPixels;
  float lineWidthScale;
  float lineWidthMinPixels;
  float lineWidthMaxPixels;
  float stroked;
  float filled;
  bool antialiasing;
  bool billboard;
  highp int radiusUnits;
  highp int lineWidthUnits;
} scatterplot;
`,d={name:"scatterplot",vs:u,fs:u,source:"",uniformTypes:{radiusScale:"f32",radiusMinPixels:"f32",radiusMaxPixels:"f32",lineWidthScale:"f32",lineWidthMinPixels:"f32",lineWidthMaxPixels:"f32",stroked:"f32",filled:"f32",antialiasing:"f32",billboard:"f32",radiusUnits:"i32",lineWidthUnits:"i32"}},p=`\
#version 300 es
#define SHADER_NAME scatterplot-layer-vertex-shader
in vec3 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in float instanceRadius;
in float instanceLineWidths;
in vec4 instanceFillColors;
in vec4 instanceLineColors;
in vec3 instancePickingColors;
out vec4 vFillColor;
out vec4 vLineColor;
out vec2 unitPosition;
out float innerUnitRadius;
out float outerRadiusPixels;
void main(void) {
geometry.worldPosition = instancePositions;
outerRadiusPixels = clamp(
project_size_to_pixel(scatterplot.radiusScale * instanceRadius, scatterplot.radiusUnits),
scatterplot.radiusMinPixels, scatterplot.radiusMaxPixels
);
float lineWidthPixels = clamp(
project_size_to_pixel(scatterplot.lineWidthScale * instanceLineWidths, scatterplot.lineWidthUnits),
scatterplot.lineWidthMinPixels, scatterplot.lineWidthMaxPixels
);
outerRadiusPixels += scatterplot.stroked * lineWidthPixels / 2.0;
float edgePadding = scatterplot.antialiasing ? (outerRadiusPixels + SMOOTH_EDGE_RADIUS) / outerRadiusPixels : 1.0;
unitPosition = edgePadding * positions.xy;
geometry.uv = unitPosition;
geometry.pickingColor = instancePickingColors;
innerUnitRadius = 1.0 - scatterplot.stroked * lineWidthPixels / outerRadiusPixels;
if (scatterplot.billboard) {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = edgePadding * positions * outerRadiusPixels;
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset = edgePadding * positions * project_pixel_size(outerRadiusPixels);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
vFillColor = vec4(instanceFillColors.rgb, instanceFillColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vFillColor, geometry);
vLineColor = vec4(instanceLineColors.rgb, instanceLineColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vLineColor, geometry);
}
`,g=`\
#version 300 es
#define SHADER_NAME scatterplot-layer-fragment-shader
precision highp float;
in vec4 vFillColor;
in vec4 vLineColor;
in vec2 unitPosition;
in float innerUnitRadius;
in float outerRadiusPixels;
out vec4 fragColor;
void main(void) {
geometry.uv = unitPosition;
float distToCenter = length(unitPosition) * outerRadiusPixels;
float inCircle = scatterplot.antialiasing ?
smoothedge(distToCenter, outerRadiusPixels) :
step(distToCenter, outerRadiusPixels);
if (inCircle == 0.0) {
discard;
}
if (scatterplot.stroked > 0.5) {
float isLine = scatterplot.antialiasing ?
smoothedge(innerUnitRadius * outerRadiusPixels, distToCenter) :
step(innerUnitRadius * outerRadiusPixels, distToCenter);
if (scatterplot.filled > 0.5) {
fragColor = mix(vFillColor, vLineColor, isLine);
} else {
if (isLine == 0.0) {
discard;
}
fragColor = vec4(vLineColor.rgb, vLineColor.a * isLine);
}
} else if (scatterplot.filled < 0.5) {
discard;
} else {
fragColor = vFillColor;
}
fragColor.a *= inCircle;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,f=`\
// Main shaders

struct ScatterplotUniforms {
  radiusScale: f32,
  radiusMinPixels: f32,
  radiusMaxPixels: f32,
  lineWidthScale: f32,
  lineWidthMinPixels: f32,
  lineWidthMaxPixels: f32,
  stroked: f32,
  filled: i32,
  antialiasing: i32,
  billboard: i32,
  radiusUnits: i32,
  lineWidthUnits: i32,
};

struct ConstantAttributeUniforms {
 instancePositions: vec3<f32>,
 instancePositions64Low: vec3<f32>,
 instanceRadius: f32,
 instanceLineWidths: f32,
 instanceFillColors: vec4<f32>,
 instanceLineColors: vec4<f32>,
 instancePickingColors: vec3<f32>,

 instancePositionsConstant: i32,
 instancePositions64LowConstant: i32,
 instanceRadiusConstant: i32,
 instanceLineWidthsConstant: i32,
 instanceFillColorsConstant: i32,
 instanceLineColorsConstant: i32,
 instancePickingColorsConstant: i32
};

@group(0) @binding(2) var<uniform> scatterplot: ScatterplotUniforms;

struct ConstantAttributes {
  instancePositions: vec3<f32>,
  instancePositions64Low: vec3<f32>,
  instanceRadius: f32,
  instanceLineWidths: f32,
  instanceFillColors: vec4<f32>,
  instanceLineColors: vec4<f32>,
  instancePickingColors: vec3<f32>
};

const constants = ConstantAttributes(
  vec3<f32>(0.0),
  vec3<f32>(0.0),
  0.0,
  0.0,
  vec4<f32>(0.0, 0.0, 0.0, 1.0),
  vec4<f32>(0.0, 0.0, 0.0, 1.0),
  vec3<f32>(0.0)
);

struct Attributes {
  @builtin(instance_index) instanceIndex : u32,
  @builtin(vertex_index) vertexIndex : u32,
  @location(0) positions: vec3<f32>,
  @location(1) instancePositions: vec3<f32>,
  @location(2) instancePositions64Low: vec3<f32>,
  @location(3) instanceRadius: f32,
  @location(4) instanceLineWidths: f32,
  @location(5) instanceFillColors: vec4<f32>,
  @location(6) instanceLineColors: vec4<f32>,
  @location(7) instancePickingColors: vec3<f32>
};

struct Varyings {
  @builtin(position) position: vec4<f32>,
  @location(0) vFillColor: vec4<f32>,
  @location(1) vLineColor: vec4<f32>,
  @location(2) unitPosition: vec2<f32>,
  @location(3) innerUnitRadius: f32,
  @location(4) outerRadiusPixels: f32,
};

@vertex
fn vertexMain(attributes: Attributes) -> Varyings {
  var varyings: Varyings;

  // Draw an inline geometry constant array clip space triangle to verify that rendering works.
  // var positions = array<vec2<f32>, 3>(vec2(0.0, 0.5), vec2(-0.5, -0.5), vec2(0.5, -0.5));
  // if (attributes.instanceIndex == 0) {
  //   varyings.position = vec4<f32>(positions[attributes.vertexIndex], 0.0, 1.0);
  //   return varyings;
  // }

  // var geometry: Geometry;
  // geometry.worldPosition = instancePositions;

  // Multiply out radius and clamp to limits
  varyings.outerRadiusPixels = clamp(
    project_unit_size_to_pixel(scatterplot.radiusScale * attributes.instanceRadius, scatterplot.radiusUnits),
    scatterplot.radiusMinPixels, scatterplot.radiusMaxPixels
  );

  // Multiply out line width and clamp to limits
  let lineWidthPixels = clamp(
    project_unit_size_to_pixel(scatterplot.lineWidthScale * attributes.instanceLineWidths, scatterplot.lineWidthUnits),
    scatterplot.lineWidthMinPixels, scatterplot.lineWidthMaxPixels
  );

  // outer radius needs to offset by half stroke width
  varyings.outerRadiusPixels += scatterplot.stroked * lineWidthPixels / 2.0;
  // Expand geometry to accommodate edge smoothing
  let edgePadding = select(
    (varyings.outerRadiusPixels + SMOOTH_EDGE_RADIUS) / varyings.outerRadiusPixels,
    1.0,
    scatterplot.antialiasing != 0
  );

  // position on the containing square in [-1, 1] space
  varyings.unitPosition = edgePadding * attributes.positions.xy;
  geometry.uv = varyings.unitPosition;
  geometry.pickingColor = attributes.instancePickingColors;

  varyings.innerUnitRadius = 1.0 - scatterplot.stroked * lineWidthPixels / varyings.outerRadiusPixels;

  if (scatterplot.billboard != 0) {
    varyings.position = project_position_to_clipspace(attributes.instancePositions, attributes.instancePositions64Low, vec3<f32>(0.0)); // TODO , geometry.position);
    // DECKGL_FILTER_GL_POSITION(varyings.position, geometry);
    let offset = attributes.positions; // * edgePadding * varyings.outerRadiusPixels;
    // DECKGL_FILTER_SIZE(offset, geometry);
    let clipPixels = project_pixel_size_to_clipspace(offset.xy);
    varyings.position.x = clipPixels.x;
    varyings.position.y = clipPixels.y;
  } else {
    let offset = edgePadding * attributes.positions * project_pixel_size_float(varyings.outerRadiusPixels);
    // DECKGL_FILTER_SIZE(offset, geometry);
    varyings.position = project_position_to_clipspace(attributes.instancePositions, attributes.instancePositions64Low, offset); // TODO , geometry.position);
    // DECKGL_FILTER_GL_POSITION(varyings.position, geometry);
  }

  // Apply opacity to instance color, or return instance picking color
  varyings.vFillColor = vec4<f32>(attributes.instanceFillColors.rgb, attributes.instanceFillColors.a * color.opacity);
  // DECKGL_FILTER_COLOR(varyings.vFillColor, geometry);
  varyings.vLineColor = vec4<f32>(attributes.instanceLineColors.rgb, attributes.instanceLineColors.a * color.opacity);
  // DECKGL_FILTER_COLOR(varyings.vLineColor, geometry);

  return varyings;
}

@fragment
fn fragmentMain(varyings: Varyings) -> @location(0) vec4<f32> {
  // var geometry: Geometry;
  // geometry.uv = unitPosition;

  let distToCenter = length(varyings.unitPosition) * varyings.outerRadiusPixels;
  let inCircle = select(
    smoothedge(distToCenter, varyings.outerRadiusPixels),
    step(distToCenter, varyings.outerRadiusPixels),
    scatterplot.antialiasing != 0
  );

  if (inCircle == 0.0) {
    discard;
  }

  var fragColor: vec4<f32>;

  if (scatterplot.stroked != 0) {
    let isLine = select(
      smoothedge(varyings.innerUnitRadius * varyings.outerRadiusPixels, distToCenter),
      step(varyings.innerUnitRadius * varyings.outerRadiusPixels, distToCenter),
      scatterplot.antialiasing != 0
    );

    if (scatterplot.filled != 0) {
      fragColor = mix(varyings.vFillColor, varyings.vLineColor, isLine);
    } else {
      if (isLine == 0.0) {
        discard;
      }
      fragColor = vec4<f32>(varyings.vLineColor.rgb, varyings.vLineColor.a * isLine);
    }
  } else if (scatterplot.filled == 0) {
    discard;
  } else {
    fragColor = varyings.vFillColor;
  }

  fragColor.a *= inCircle;
  // DECKGL_FILTER_COLOR(fragColor, geometry);

  // Apply premultiplied alpha as required by transparent canvas
  fragColor = deckgl_premultiplied_alpha(fragColor);

  return fragColor;
  // return vec4<f32>(0, 0, 1, 1);
}
`,h=[0,0,0,255],v={radiusUnits:"meters",radiusScale:{type:"number",min:0,value:1},radiusMinPixels:{type:"number",min:0,value:0},radiusMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},lineWidthUnits:"meters",lineWidthScale:{type:"number",min:0,value:1},lineWidthMinPixels:{type:"number",min:0,value:0},lineWidthMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},stroked:!1,filled:!0,billboard:!1,antialiasing:!0,getPosition:{type:"accessor",value:e=>e.position},getRadius:{type:"accessor",value:1},getFillColor:{type:"accessor",value:h},getLineColor:{type:"accessor",value:h},getLineWidth:{type:"accessor",value:1},strokeWidth:{deprecatedFor:"getLineWidth"},outline:{deprecatedFor:"stroked"},getColor:{deprecatedFor:["getFillColor","getLineColor"]}};class x extends o.A{getShaders(){return super.getShaders({vs:p,fs:g,source:f,modules:[n.A,s.A,r.A,d]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceRadius:{size:1,transition:!0,accessor:"getRadius",defaultValue:1},instanceFillColors:{size:this.props.colorFormat.length,transition:!0,type:"unorm8",accessor:"getFillColor",defaultValue:[0,0,0,255]},instanceLineColors:{size:this.props.colorFormat.length,transition:!0,type:"unorm8",accessor:"getLineColor",defaultValue:[0,0,0,255]},instanceLineWidths:{size:1,transition:!0,accessor:"getLineWidth",defaultValue:1}})}updateState(e){super.updateState(e),e.changeFlags.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:e}){let{radiusUnits:t,radiusScale:i,radiusMinPixels:o,radiusMaxPixels:n,stroked:s,filled:r,billboard:l,antialiasing:c,lineWidthUnits:u,lineWidthScale:d,lineWidthMinPixels:p,lineWidthMaxPixels:g}=this.props,f={stroked:s,filled:r,billboard:l,antialiasing:c,radiusUnits:a.p5[t],radiusScale:i,radiusMinPixels:o,radiusMaxPixels:n,lineWidthUnits:a.p5[u],lineWidthScale:d,lineWidthMinPixels:p,lineWidthMaxPixels:g},h=this.state.model;h.shaderInputs.setProps({scatterplot:f}),"webgpu"===this.context.device.type&&(h.instanceCount=this.props.data.length),h.draw(this.context.renderPass)}_getModel(){let e="webgpu"===this.context.device.type?{depthWriteEnabled:!0,depthCompare:"less-equal"}:void 0;return new l.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new c.V({topology:"triangle-strip",attributes:{positions:{size:3,value:new Float32Array([-1,-1,0,1,-1,0,-1,1,0,1,1,0])}}}),isInstanced:!0,parameters:e})}}x.defaultProps=v,x.layerName="ScatterplotLayer";let y=x},55596:(e,t,i)=>{i.d(t,{$q:()=>h,A4:()=>c,Dt:()=>l,S8:()=>p});var o=i(24540),n=i(95952);let s=n.rJ.CLOCKWISE,r=n.rJ.COUNTER_CLOCKWISE,a={isClosed:!0};function l(e){return"positions"in e?e.positions:e}function c(e){return"holeIndices"in e?e.holeIndices:null}function u(e,t,i,o,s){let r=t,l=i.length;for(let t=0;t<l;t++)for(let n=0;n<o;n++)e[r++]=i[t][n]||0;if(!function(e){let t=e[0],i=e[e.length-1];return t[0]===i[0]&&t[1]===i[1]&&t[2]===i[2]}(i))for(let t=0;t<o;t++)e[r++]=i[0][t]||0;return a.start=t,a.end=r,a.size=o,(0,n.UD)(e,s,a),r}function d(e,t,i,o,s=0,r,l){let c=(r=r||i.length)-s;if(c<=0)return t;let u=t;for(let t=0;t<c;t++)e[u++]=i[s+t];if(!function(e,t,i,o){for(let n=0;n<t;n++)if(e[i+n]!==e[o-t+n])return!1;return!0}(i,o,s,r))for(let t=0;t<o;t++)e[u++]=i[s+t];return a.start=t,a.end=u,a.size=o,(0,n.UD)(e,l,a),u}function p(e,t){var i;!function(e){if(!Array.isArray(e=e&&e.positions||e)&&!ArrayBuffer.isView(e))throw Error("invalid polygon")}(e);let o=[],n=[];if("positions"in e){let{positions:i,holeIndices:a}=e;if(a){let e=0;for(let l=0;l<=a.length;l++)e=d(o,e,i,t,a[l-1],a[l],0===l?s:r),n.push(e);return n.pop(),{positions:o,holeIndices:n}}e=i}if(!Array.isArray(e[0]))return d(o,0,e,t,0,o.length,s),o;if(!((i=e).length>=1&&i[0].length>=2&&Number.isFinite(i[0][0]))){let i=0;for(let[a,l]of e.entries())i=u(o,i,l,t,0===a?s:r),n.push(i);return n.pop(),{positions:o,holeIndices:n}}return u(o,0,e,t,s),o}function g(e,t,i){let o=e.length/3,n=0;for(let s=0;s<o;s++){let r=(s+1)%o;n+=e[3*s+t]*e[3*r+i],n-=e[3*r+t]*e[3*s+i]}return Math.abs(n/2)}function f(e,t,i,o){let n=e.length/3;for(let s=0;s<n;s++){let n=3*s,r=e[n+0],a=e[n+1],l=e[n+2];e[n+t]=r,e[n+i]=a,e[n+o]=l}}function h(e,t,i,n){let s=c(e);s&&(s=s.map(e=>e/t));let r=l(e),a=n&&3===t;if(i){let e=r.length;r=r.slice();let o=[];for(let n=0;n<e;n+=t){o[0]=r[n],o[1]=r[n+1],a&&(o[2]=r[n+2]);let e=i(o);r[n]=e[0],r[n+1]=e[1],a&&(r[n+2]=e[2])}}if(a){let e=g(r,0,1),t=g(r,0,2),o=g(r,1,2);if(!e&&!t&&!o)return[];e>t&&e>o||(t>o?(i||(r=r.slice()),f(r,0,2,1)):(i||(r=r.slice()),f(r,2,0,1)))}return o(r,s,t)}},82940:(e,t,i)=>{i.d(t,{A:()=>b});var o=i(98318),n=i(2854),s=i(65489),r=i(60303),a=i(91538),l=i(88912),c=i(75817),u=i(55596),d=i(53028),p=i(95952);class g extends d.A{constructor(e){let{fp64:t,IndexType:i=Uint32Array}=e;super({...e,attributes:{positions:{size:3,type:t?Float64Array:Float32Array},vertexValid:{type:Uint16Array,size:1},indices:{type:i,size:1}}})}get(e){let{attributes:t}=this;return"indices"===e?t.indices&&t.indices.subarray(0,this.vertexCount):t[e]}updateGeometry(e){super.updateGeometry(e);let t=this.buffers.indices;if(t)this.vertexCount=(t.value||t).length;else if(this.data&&!this.getGeometry)throw Error("missing indices buffer")}normalizeGeometry(e){if(this.normalize){let t=u.S8(e,this.positionSize);return this.opts.resolution?(0,p.wk)(u.Dt(t),u.A4(t),{size:this.positionSize,gridResolution:this.opts.resolution,edgeTypes:!0}):this.opts.wrapLongitude?(0,p.Eg)(u.Dt(t),u.A4(t),{size:this.positionSize,maxLatitude:86,edgeTypes:!0}):t}return e}getGeometrySize(e){if(f(e)){let t=0;for(let i of e)t+=this.getGeometrySize(i);return t}return u.Dt(e).length/this.positionSize}getGeometryFromBuffer(e){return this.normalize||!this.buffers.indices?super.getGeometryFromBuffer(e):null}updateGeometryAttributes(e,t){if(e&&f(e))for(let i of e){let e=this.getGeometrySize(i);t.geometrySize=e,this.updateGeometryAttributes(i,t),t.vertexStart+=e,t.indexStart=this.indexStarts[t.geometryIndex+1]}else this._updateIndices(e,t),this._updatePositions(e,t),this._updateVertexValid(e,t)}_updateIndices(e,{geometryIndex:t,vertexStart:i,indexStart:o}){let{attributes:n,indexStarts:s,typedArrayManager:r}=this,a=n.indices;if(!a||!e)return;let l=o,c=u.$q(e,this.positionSize,this.opts.preproject,this.opts.full3d);a=r.allocate(a,o+c.length,{copy:!0});for(let e=0;e<c.length;e++)a[l++]=c[e]+i;s[t+1]=o+c.length,n.indices=a}_updatePositions(e,{vertexStart:t,geometrySize:i}){let{attributes:{positions:o},positionSize:n}=this;if(!o||!e)return;let s=u.Dt(e);for(let e=t,r=0;r<i;e++,r++){let t=s[r*n],i=s[r*n+1],a=n>2?s[r*n+2]:0;o[3*e]=t,o[3*e+1]=i,o[3*e+2]=a}}_updateVertexValid(e,{vertexStart:t,geometrySize:i}){let{positionSize:o}=this,n=this.attributes.vertexValid,s=e&&u.A4(e);if(e&&e.edgeTypes?n.set(e.edgeTypes,t):n.fill(1,t,t+i),s)for(let e=0;e<s.length;e++)n[t+s[e]/o-1]=0;n[t+i-1]=0}}function f(e){return Array.isArray(e)&&e.length>0&&!Number.isFinite(e[0])}let h=`\
uniform solidPolygonUniforms {
  bool extruded;
  bool isWireframe;
  float elevationScale;
} solidPolygon;
`,v={name:"solidPolygon",vs:h,fs:h,uniformTypes:{extruded:"f32",isWireframe:"f32",elevationScale:"f32"}},x=`\
in vec4 fillColors;
in vec4 lineColors;
in vec3 pickingColors;
out vec4 vColor;
struct PolygonProps {
vec3 positions;
vec3 positions64Low;
vec3 normal;
float elevations;
};
vec3 project_offset_normal(vec3 vector) {
if (project.coordinateSystem == COORDINATE_SYSTEM_LNGLAT ||
project.coordinateSystem == COORDINATE_SYSTEM_LNGLAT_OFFSETS) {
return normalize(vector * project.commonUnitsPerWorldUnit);
}
return project_normal(vector);
}
void calculatePosition(PolygonProps props) {
vec3 pos = props.positions;
vec3 pos64Low = props.positions64Low;
vec3 normal = props.normal;
vec4 colors = solidPolygon.isWireframe ? lineColors : fillColors;
geometry.worldPosition = props.positions;
geometry.pickingColor = pickingColors;
if (solidPolygon.extruded) {
pos.z += props.elevations * solidPolygon.elevationScale;
}
gl_Position = project_position_to_clipspace(pos, pos64Low, vec3(0.), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
if (solidPolygon.extruded) {
#ifdef IS_SIDE_VERTEX
normal = project_offset_normal(normal);
#else
normal = project_normal(normal);
#endif
geometry.normal = normal;
vec3 lightColor = lighting_getLightColor(colors.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);
vColor = vec4(lightColor, colors.a * layer.opacity);
} else {
vColor = vec4(colors.rgb, colors.a * layer.opacity);
}
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,y=`\
#version 300 es
#define SHADER_NAME solid-polygon-layer-vertex-shader
in vec3 vertexPositions;
in vec3 vertexPositions64Low;
in float elevations;
${x}
void main(void) {
PolygonProps props;
props.positions = vertexPositions;
props.positions64Low = vertexPositions64Low;
props.elevations = elevations;
props.normal = vec3(0.0, 0.0, 1.0);
calculatePosition(props);
}
`,m=`\
#version 300 es
#define SHADER_NAME solid-polygon-layer-vertex-shader-side
#define IS_SIDE_VERTEX
in vec2 positions;
in vec3 vertexPositions;
in vec3 nextVertexPositions;
in vec3 vertexPositions64Low;
in vec3 nextVertexPositions64Low;
in float elevations;
in float instanceVertexValid;
${x}
void main(void) {
if(instanceVertexValid < 0.5){
gl_Position = vec4(0.);
return;
}
PolygonProps props;
vec3 pos;
vec3 pos64Low;
vec3 nextPos;
vec3 nextPos64Low;
#if RING_WINDING_ORDER_CW == 1
pos = vertexPositions;
pos64Low = vertexPositions64Low;
nextPos = nextVertexPositions;
nextPos64Low = nextVertexPositions64Low;
#else
pos = nextVertexPositions;
pos64Low = nextVertexPositions64Low;
nextPos = vertexPositions;
nextPos64Low = vertexPositions64Low;
#endif
props.positions = mix(pos, nextPos, positions.x);
props.positions64Low = mix(pos64Low, nextPos64Low, positions.x);
props.normal = vec3(
pos.y - nextPos.y + (pos64Low.y - nextPos64Low.y),
nextPos.x - pos.x + (nextPos64Low.x - pos64Low.x),
0.0);
props.elevations = elevations * positions.y;
calculatePosition(props);
}
`,P=`\
#version 300 es
#define SHADER_NAME solid-polygon-layer-fragment-shader
precision highp float;
in vec4 vColor;
out vec4 fragColor;
void main(void) {
fragColor = vColor;
geometry.uv = vec2(0.);
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,_=[0,0,0,255],C={enter:(e,t)=>t.length?t.subarray(t.length-e.length):e};class L extends o.A{getShaders(e){return super.getShaders({vs:"top"===e?y:m,fs:P,defines:{RING_WINDING_ORDER_CW:this.props._normalize||"CCW"!==this.props._windingOrder?1:0},modules:[n.A,c.J,s.A,v]})}get wrapLongitude(){return!1}getBounds(){return this.getAttributeManager()?.getBounds(["vertexPositions"])}initializeState(){let e;let{viewport:t}=this.context,{coordinateSystem:i}=this.props,{_full3d:o}=this.props;t.isGeospatial&&i===r.rf.DEFAULT&&(i=r.rf.LNGLAT),i===r.rf.LNGLAT&&(e=o?t.projectPosition.bind(t):t.projectFlat.bind(t)),this.setState({numInstances:0,polygonTesselator:new g({preproject:e,fp64:this.use64bitPositions(),IndexType:Uint32Array})});let n=this.getAttributeManager();n.remove(["instancePickingColors"]),n.add({indices:{size:1,isIndexed:!0,update:this.calculateIndices,noAlloc:!0},vertexPositions:{size:3,type:"float64",stepMode:"dynamic",fp64:this.use64bitPositions(),transition:C,accessor:"getPolygon",update:this.calculatePositions,noAlloc:!0,shaderAttributes:{nextVertexPositions:{vertexOffset:1}}},instanceVertexValid:{size:1,type:"uint16",stepMode:"instance",update:this.calculateVertexValid,noAlloc:!0},elevations:{size:1,stepMode:"dynamic",transition:C,accessor:"getElevation"},fillColors:{size:this.props.colorFormat.length,type:"unorm8",stepMode:"dynamic",transition:C,accessor:"getFillColor",defaultValue:_},lineColors:{size:this.props.colorFormat.length,type:"unorm8",stepMode:"dynamic",transition:C,accessor:"getLineColor",defaultValue:_},pickingColors:{size:4,type:"uint8",stepMode:"dynamic",accessor:(e,{index:t,target:i})=>this.encodePickingColor(e&&e.__source?e.__source.index:t,i)}})}getPickingInfo(e){let t=super.getPickingInfo(e),{index:i}=t,o=this.props.data;return o[0]&&o[0].__source&&(t.object=o.find(e=>e.__source.index===i)),t}disablePickingIndex(e){let t=this.props.data;if(t[0]&&t[0].__source)for(let i=0;i<t.length;i++)t[i].__source.index===e&&this._disablePickingIndex(i);else super.disablePickingIndex(e)}draw({uniforms:e}){let{extruded:t,filled:i,wireframe:o,elevationScale:n}=this.props,{topModel:s,sideModel:r,wireframeModel:a,polygonTesselator:l}=this.state,c={extruded:!!t,elevationScale:n,isWireframe:!1};a&&o&&(a.setInstanceCount(l.instanceCount-1),a.shaderInputs.setProps({solidPolygon:{...c,isWireframe:!0}}),a.draw(this.context.renderPass)),r&&i&&(r.setInstanceCount(l.instanceCount-1),r.shaderInputs.setProps({solidPolygon:c}),r.draw(this.context.renderPass)),s&&i&&(s.setVertexCount(l.vertexCount),s.shaderInputs.setProps({solidPolygon:c}),s.draw(this.context.renderPass))}updateState(e){super.updateState(e),this.updateGeometry(e);let{props:t,oldProps:i,changeFlags:o}=e,n=this.getAttributeManager();(o.extensionsChanged||t.filled!==i.filled||t.extruded!==i.extruded)&&(this.state.models?.forEach(e=>e.destroy()),this.setState(this._getModels()),n.invalidateAll())}updateGeometry({props:e,oldProps:t,changeFlags:i}){if(i.dataChanged||i.updateTriggersChanged&&(i.updateTriggersChanged.all||i.updateTriggersChanged.getPolygon)){let{polygonTesselator:t}=this.state,o=e.data.attributes||{};t.updateGeometry({data:e.data,normalize:e._normalize,geometryBuffer:o.getPolygon,buffers:o,getGeometry:e.getPolygon,positionFormat:e.positionFormat,wrapLongitude:e.wrapLongitude,resolution:this.context.viewport.resolution,fp64:this.use64bitPositions(),dataChanged:i.dataChanged,full3d:e._full3d}),this.setState({numInstances:t.instanceCount,startIndices:t.vertexStarts}),i.dataChanged||this.getAttributeManager().invalidateAll()}}_getModels(){let e,t,i;let{id:o,filled:n,extruded:s}=this.props;if(n){let t=this.getShaders("top");t.defines.NON_INSTANCED_MODEL=1;let i=this.getAttributeManager().getBufferLayouts({isInstanced:!1});e=new a.K(this.context.device,{...t,id:`${o}-top`,topology:"triangle-list",bufferLayout:i,isIndexed:!0,userData:{excludeAttributes:{instanceVertexValid:!0}}})}if(s){let e=this.getAttributeManager().getBufferLayouts({isInstanced:!0});t=new a.K(this.context.device,{...this.getShaders("side"),id:`${o}-side`,bufferLayout:e,geometry:new l.V({topology:"triangle-strip",attributes:{positions:{size:2,value:new Float32Array([1,0,0,0,1,1,0,1])}}}),isInstanced:!0,userData:{excludeAttributes:{indices:!0}}}),i=new a.K(this.context.device,{...this.getShaders("side"),id:`${o}-wireframe`,bufferLayout:e,geometry:new l.V({topology:"line-strip",attributes:{positions:{size:2,value:new Float32Array([1,0,0,0,0,1,1,1])}}}),isInstanced:!0,userData:{excludeAttributes:{indices:!0}}})}return{models:[t,i,e].filter(Boolean),topModel:e,sideModel:t,wireframeModel:i}}calculateIndices(e){let{polygonTesselator:t}=this.state;e.startIndices=t.indexStarts,e.value=t.get("indices")}calculatePositions(e){let{polygonTesselator:t}=this.state;e.startIndices=t.vertexStarts,e.value=t.get("positions")}calculateVertexValid(e){e.value=this.state.polygonTesselator.get("vertexValid")}}L.defaultProps={filled:!0,extruded:!1,wireframe:!1,_normalize:!0,_windingOrder:"CW",_full3d:!1,elevationScale:{type:"number",min:0,value:1},getPolygon:{type:"accessor",value:e=>e.polygon},getElevation:{type:"accessor",value:1e3},getFillColor:{type:"accessor",value:_},getLineColor:{type:"accessor",value:_},material:!0},L.layerName="SolidPolygonLayer";let b=L},83661:(e,t,i)=>{i.d(t,{A:()=>u});var o=i(77002),n=i(60738);let s=`\
uniform sdfUniforms {
  float gamma;
  bool enabled;
  float buffer;
  float outlineBuffer;
  vec4 outlineColor;
} sdf;
`,r={name:"sdf",vs:s,fs:s,uniformTypes:{gamma:"f32",enabled:"f32",buffer:"f32",outlineBuffer:"f32",outlineColor:"vec4<f32>"}},a=`\
#version 300 es
#define SHADER_NAME multi-icon-layer-fragment-shader
precision highp float;
uniform sampler2D iconsTexture;
in vec4 vColor;
in vec2 vTextureCoords;
in vec2 uv;
out vec4 fragColor;
void main(void) {
geometry.uv = uv;
if (!bool(picking.isActive)) {
float alpha = texture(iconsTexture, vTextureCoords).a;
vec4 color = vColor;
if (sdf.enabled) {
float distance = alpha;
alpha = smoothstep(sdf.buffer - sdf.gamma, sdf.buffer + sdf.gamma, distance);
if (sdf.outlineBuffer > 0.0) {
float inFill = alpha;
float inBorder = smoothstep(sdf.outlineBuffer - sdf.gamma, sdf.outlineBuffer + sdf.gamma, distance);
color = mix(sdf.outlineColor, vColor, inFill);
alpha = inBorder;
}
}
float a = alpha * color.a;
if (a < icon.alphaCutoff) {
discard;
}
fragColor = vec4(color.rgb, a * layer.opacity);
}
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,l=[];class c extends n.A{getShaders(){let e=super.getShaders();return{...e,modules:[...e.modules,r],fs:a}}initializeState(){super.initializeState(),this.getAttributeManager().addInstanced({instanceOffsets:{size:2,accessor:"getIconOffsets"},instancePickingColors:{type:"uint8",size:3,accessor:(e,{index:t,target:i})=>this.encodePickingColor(t,i)}})}updateState(e){super.updateState(e);let{props:t,oldProps:i}=e,{outlineColor:n}=t;if(n!==i.outlineColor){let e=[n[0]/255,n[1]/255,n[2]/255,(n[3]??255)/255];this.setState({outlineColor:e})}!t.sdf&&t.outlineWidth&&o.A.warn(`${this.id}: fontSettings.sdf is required to render outline`)()}draw(e){let{sdf:t,smoothing:i,outlineWidth:o}=this.props,{outlineColor:n}=this.state,s=o?Math.max(i,.75*(1-o)):-1,r=this.state.model,a={buffer:.75,outlineBuffer:s,gamma:i,enabled:!!t,outlineColor:n};if(r.shaderInputs.setProps({sdf:a}),super.draw(e),t&&o){let{iconManager:e}=this.state;e.getTexture()&&(r.shaderInputs.setProps({sdf:{...a,outlineBuffer:.75}}),r.draw(this.context.renderPass))}}getInstanceOffset(e){return e?Array.from(e).flatMap(e=>super.getInstanceOffset(e)):l}getInstanceColorMode(e){return 1}getInstanceIconFrame(e){return e?Array.from(e).flatMap(e=>super.getInstanceIconFrame(e)):l}}c.defaultProps={getIconOffsets:{type:"accessor",value:e=>e.offsets},alphaCutoff:.001,smoothing:.1,outlineWidth:0,outlineColor:{type:"color",value:[0,0,0,255]}},c.layerName="MultiIconLayer";let u=c},10009:(e,t,i)=>{i.d(t,{A:()=>h});var o=i(98318),n=i(2854),s=i(65489),r=i(60303),a=i(88912),l=i(91538);let c=`\
uniform textBackgroundUniforms {
  bool billboard;
  float sizeScale;
  float sizeMinPixels;
  float sizeMaxPixels;
  vec4 borderRadius;
  vec4 padding;
  highp int sizeUnits;
  bool stroked;
} textBackground;
`,u={name:"textBackground",vs:c,fs:c,uniformTypes:{billboard:"f32",sizeScale:"f32",sizeMinPixels:"f32",sizeMaxPixels:"f32",borderRadius:"vec4<f32>",padding:"vec4<f32>",sizeUnits:"i32",stroked:"f32"}},d=`\
#version 300 es
#define SHADER_NAME text-background-layer-vertex-shader
in vec2 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in vec4 instanceRects;
in float instanceSizes;
in float instanceAngles;
in vec2 instancePixelOffsets;
in float instanceLineWidths;
in vec4 instanceFillColors;
in vec4 instanceLineColors;
in vec3 instancePickingColors;
out vec4 vFillColor;
out vec4 vLineColor;
out float vLineWidth;
out vec2 uv;
out vec2 dimensions;
vec2 rotate_by_angle(vec2 vertex, float angle) {
float angle_radian = radians(angle);
float cos_angle = cos(angle_radian);
float sin_angle = sin(angle_radian);
mat2 rotationMatrix = mat2(cos_angle, -sin_angle, sin_angle, cos_angle);
return rotationMatrix * vertex;
}
void main(void) {
geometry.worldPosition = instancePositions;
geometry.uv = positions;
geometry.pickingColor = instancePickingColors;
uv = positions;
vLineWidth = instanceLineWidths;
float sizePixels = clamp(
project_size_to_pixel(instanceSizes * textBackground.sizeScale, textBackground.sizeUnits),
textBackground.sizeMinPixels, textBackground.sizeMaxPixels
);
dimensions = instanceRects.zw * sizePixels + textBackground.padding.xy + textBackground.padding.zw;
vec2 pixelOffset = (positions * instanceRects.zw + instanceRects.xy) * sizePixels + mix(-textBackground.padding.xy, textBackground.padding.zw, positions);
pixelOffset = rotate_by_angle(pixelOffset, instanceAngles);
pixelOffset += instancePixelOffsets;
pixelOffset.y *= -1.0;
if (textBackground.billboard)  {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = vec3(pixelOffset, 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset_common = vec3(project_pixel_size(pixelOffset), 0.0);
DECKGL_FILTER_SIZE(offset_common, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset_common, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
vFillColor = vec4(instanceFillColors.rgb, instanceFillColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vFillColor, geometry);
vLineColor = vec4(instanceLineColors.rgb, instanceLineColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vLineColor, geometry);
}
`,p=`\
#version 300 es
#define SHADER_NAME text-background-layer-fragment-shader
precision highp float;
in vec4 vFillColor;
in vec4 vLineColor;
in float vLineWidth;
in vec2 uv;
in vec2 dimensions;
out vec4 fragColor;
float round_rect(vec2 p, vec2 size, vec4 radii) {
vec2 pixelPositionCB = (p - 0.5) * size;
vec2 sizeCB = size * 0.5;
float maxBorderRadius = min(size.x, size.y) * 0.5;
vec4 borderRadius = vec4(min(radii, maxBorderRadius));
borderRadius.xy =
(pixelPositionCB.x > 0.0) ? borderRadius.xy : borderRadius.zw;
borderRadius.x = (pixelPositionCB.y > 0.0) ? borderRadius.x : borderRadius.y;
vec2 q = abs(pixelPositionCB) - sizeCB + borderRadius.x;
return -(min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - borderRadius.x);
}
float rect(vec2 p, vec2 size) {
vec2 pixelPosition = p * size;
return min(min(pixelPosition.x, size.x - pixelPosition.x),
min(pixelPosition.y, size.y - pixelPosition.y));
}
vec4 get_stroked_fragColor(float dist) {
float isBorder = smoothedge(dist, vLineWidth);
return mix(vFillColor, vLineColor, isBorder);
}
void main(void) {
geometry.uv = uv;
if (textBackground.borderRadius != vec4(0.0)) {
float distToEdge = round_rect(uv, dimensions, textBackground.borderRadius);
if (textBackground.stroked) {
fragColor = get_stroked_fragColor(distToEdge);
} else {
fragColor = vFillColor;
}
float shapeAlpha = smoothedge(-distToEdge, 0.0);
fragColor.a *= shapeAlpha;
} else {
if (textBackground.stroked) {
float distToEdge = rect(uv, dimensions);
fragColor = get_stroked_fragColor(distToEdge);
} else {
fragColor = vFillColor;
}
}
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,g={billboard:!0,sizeScale:1,sizeUnits:"pixels",sizeMinPixels:0,sizeMaxPixels:Number.MAX_SAFE_INTEGER,borderRadius:{type:"object",value:0},padding:{type:"array",value:[0,0,0,0]},getPosition:{type:"accessor",value:e=>e.position},getSize:{type:"accessor",value:1},getAngle:{type:"accessor",value:0},getPixelOffset:{type:"accessor",value:[0,0]},getBoundingRect:{type:"accessor",value:[0,0,0,0]},getFillColor:{type:"accessor",value:[0,0,0,255]},getLineColor:{type:"accessor",value:[0,0,0,255]},getLineWidth:{type:"accessor",value:1}};class f extends o.A{getShaders(){return super.getShaders({vs:d,fs:p,modules:[n.A,s.A,u]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceSizes:{size:1,transition:!0,accessor:"getSize",defaultValue:1},instanceAngles:{size:1,transition:!0,accessor:"getAngle"},instanceRects:{size:4,accessor:"getBoundingRect"},instancePixelOffsets:{size:2,transition:!0,accessor:"getPixelOffset"},instanceFillColors:{size:4,transition:!0,type:"unorm8",accessor:"getFillColor",defaultValue:[0,0,0,255]},instanceLineColors:{size:4,transition:!0,type:"unorm8",accessor:"getLineColor",defaultValue:[0,0,0,255]},instanceLineWidths:{size:1,transition:!0,accessor:"getLineWidth",defaultValue:1}})}updateState(e){super.updateState(e);let{changeFlags:t}=e;t.extensionsChanged&&(this.state.model?.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:e}){let{billboard:t,sizeScale:i,sizeUnits:o,sizeMinPixels:n,sizeMaxPixels:s,getLineWidth:a}=this.props,{padding:l,borderRadius:c}=this.props;l.length<4&&(l=[l[0],l[1],l[0],l[1]]),Array.isArray(c)||(c=[c,c,c,c]);let u=this.state.model,d={billboard:t,stroked:!!a,borderRadius:c,padding:l,sizeUnits:r.p5[o],sizeScale:i,sizeMinPixels:n,sizeMaxPixels:s};u.shaderInputs.setProps({textBackground:d}),u.draw(this.context.renderPass)}_getModel(){return new l.K(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new a.V({topology:"triangle-strip",vertexCount:4,attributes:{positions:{size:2,value:new Float32Array([0,0,1,0,0,1,1,1])}}}),isInstanced:!0})}}f.defaultProps=g,f.layerName="TextBackgroundLayer";let h=f},19188:(e,t,i)=>{i.d(t,{A:()=>b});var o=i(24125),n=i(77002),s=i(98614),r=i(83661);class a{constructor({fontSize:e=24,buffer:t=3,radius:i=8,cutoff:o=.25,fontFamily:n="sans-serif",fontWeight:s="normal",fontStyle:r="normal",lang:a=null}={}){this.buffer=t,this.cutoff=o,this.radius=i,this.lang=a;let l=this.size=e+4*t,c=this._createCanvas(l),u=this.ctx=c.getContext("2d",{willReadFrequently:!0});u.font=`${r} ${s} ${e}px ${n}`,u.textBaseline="alphabetic",u.textAlign="left",u.fillStyle="black",this.gridOuter=new Float64Array(l*l),this.gridInner=new Float64Array(l*l),this.f=new Float64Array(l),this.z=new Float64Array(l+1),this.v=new Uint16Array(l)}_createCanvas(e){let t=document.createElement("canvas");return t.width=t.height=e,t}draw(e){let{width:t,actualBoundingBoxAscent:i,actualBoundingBoxDescent:o,actualBoundingBoxLeft:n,actualBoundingBoxRight:s}=this.ctx.measureText(e),r=Math.ceil(i),a=Math.max(0,Math.min(this.size-this.buffer,Math.ceil(s-n))),c=Math.min(this.size-this.buffer,r+Math.ceil(o)),u=a+2*this.buffer,d=c+2*this.buffer,p=Math.max(u*d,0),g=new Uint8ClampedArray(p),f={data:g,width:u,height:d,glyphWidth:a,glyphHeight:c,glyphTop:r,glyphLeft:0,glyphAdvance:t};if(0===a||0===c)return f;let{ctx:h,buffer:v,gridInner:x,gridOuter:y}=this;this.lang&&(h.lang=this.lang),h.clearRect(v,v,a,c),h.fillText(e,v,v+r);let m=h.getImageData(v,v,a,c);y.fill(1e20,0,p),x.fill(0,0,p);for(let e=0;e<c;e++)for(let t=0;t<a;t++){let i=m.data[4*(e*a+t)+3]/255;if(0===i)continue;let o=(e+v)*u+t+v;if(1===i)y[o]=0,x[o]=1e20;else{let e=.5-i;y[o]=e>0?e*e:0,x[o]=e<0?e*e:0}}l(y,0,0,u,d,u,this.f,this.v,this.z),l(x,v,v,a,c,u,this.f,this.v,this.z);for(let e=0;e<p;e++){let t=Math.sqrt(y[e])-Math.sqrt(x[e]);g[e]=Math.round(255-255*(t/this.radius+this.cutoff))}return f}}function l(e,t,i,o,n,s,r,a,l){for(let u=t;u<t+o;u++)c(e,i*s+u,s,n,r,a,l);for(let u=i;u<i+n;u++)c(e,u*s+t,1,o,r,a,l)}function c(e,t,i,o,n,s,r){s[0]=0,r[0]=-1e20,r[1]=1e20,n[0]=e[t];for(let a=1,l=0,c=0;a<o;a++){n[a]=e[t+a*i];let o=a*a;do{let e=s[l];c=(n[a]-n[e]+o-e*e)/(a-e)/2}while(c<=r[l]&&--l>-1);s[++l]=a,r[l]=c,r[l+1]=1e20}for(let a=0,l=0;a<o;a++){for(;r[l+1]<a;)l++;let o=s[l],c=a-o;e[t+a*i]=n[o]+c*c}}let u=[];function d(e,t,i,o){let n=0;for(let s=t;s<i;s++){let t=e[s];n+=o[t]?.layoutWidth||0}return n}function p(e,t,i,o,n,s){let r=t,a=0;for(let l=t;l<i;l++){let t=d(e,l,l+1,n);a+t>o&&(r<l&&s.push(l),r=l,a=0),a+=t}return a}class g{constructor(e=5){this._cache={},this._order=[],this.limit=e}get(e){let t=this._cache[e];return t&&(this._deleteOrder(e),this._appendOrder(e)),t}set(e,t){this._cache[e]?this.delete(e):Object.keys(this._cache).length===this.limit&&this.delete(this._order[0]),this._cache[e]=t,this._appendOrder(e)}delete(e){this._cache[e]&&(delete this._cache[e],this._deleteOrder(e))}_deleteOrder(e){let t=this._order.indexOf(e);t>=0&&this._order.splice(t,1)}_appendOrder(e){this._order.push(e)}}let f={fontFamily:"Monaco, monospace",fontWeight:"normal",characterSet:function(){let e=[];for(let t=32;t<128;t++)e.push(String.fromCharCode(t));return e}(),fontSize:64,buffer:4,sdf:!1,cutoff:.25,radius:12,smoothing:.1},h=new g(3);function v(e,t,i,o){e.font=`${o} ${i}px ${t}`,e.fillStyle="#000",e.textBaseline="alphabetic",e.textAlign="left"}class x{constructor(){this.props={...f}}get atlas(){return this._atlas}get mapping(){return this._atlas&&this._atlas.mapping}get scale(){let{fontSize:e,buffer:t}=this.props;return(1.2*e+2*t)/e}setProps(e={}){Object.assign(this.props,e),this._key=this._getKey();let t=function(e,t){let i;i=new Set("string"==typeof t?Array.from(t):t);let o=h.get(e);if(!o)return i;for(let e in o.mapping)i.has(e)&&i.delete(e);return i}(this._key,this.props.characterSet),i=h.get(this._key);if(i&&0===t.size){this._atlas!==i&&(this._atlas=i);return}let o=this._generateFontAtlas(t,i);this._atlas=o,h.set(this._key,o)}_generateFontAtlas(e,t){let{fontFamily:i,fontWeight:o,fontSize:n,buffer:s,sdf:r,radius:l,cutoff:c}=this.props,u=t&&t.data;u||((u=document.createElement("canvas")).width=1024);let d=u.getContext("2d",{willReadFrequently:!0});v(d,i,n,o);let{mapping:p,canvasHeight:g,xOffset:f,yOffset:h}=function({characterSet:e,getFontWidth:t,fontHeight:i,buffer:o,maxCanvasWidth:n,mapping:s={},xOffset:r=0,yOffset:a=0}){let l=0,c=r,u=i+2*o;for(let r of e)if(!s[r]){let e=t(r);c+e+2*o>n&&(c=0,l++),s[r]={x:c+o,y:a+l*u+o,width:e,height:u,layoutWidth:e,layoutHeight:i},c+=e+2*o}return{mapping:s,xOffset:c,yOffset:a+l*u,canvasHeight:Math.pow(2,Math.ceil(Math.log2(a+(l+1)*u)))}}({getFontWidth:e=>d.measureText(e).width,fontHeight:1.2*n,buffer:s,characterSet:e,maxCanvasWidth:1024,...t&&{mapping:t.mapping,xOffset:t.xOffset,yOffset:t.yOffset}});if(u.height!==g){let e=d.getImageData(0,0,u.width,u.height);u.height=g,d.putImageData(e,0,0)}if(v(d,i,n,o),r){let t=new a({fontSize:n,buffer:s,radius:l,cutoff:c,fontFamily:i,fontWeight:`${o}`});for(let i of e){let{data:e,width:o,height:s,glyphTop:r}=t.draw(i);p[i].width=o,p[i].layoutOffsetY=.9*n-r;let a=d.createImageData(o,s);!function(e,t){for(let i=0;i<e.length;i++)t.data[4*i+3]=e[i]}(e,a),d.putImageData(a,p[i].x,p[i].y)}}else for(let t of e)d.fillText(t,p[t].x,p[t].y+s+.9*n);return{xOffset:f,yOffset:h,mapping:p,data:u,width:u.width,height:u.height}}_getKey(){let{fontFamily:e,fontWeight:t,fontSize:i,buffer:o,sdf:n,radius:s,cutoff:r}=this.props;return n?`${e} ${t} ${i} ${o} ${s} ${r}`:`${e} ${t} ${i} ${o}`}}var y=i(10009);let m={start:1,middle:0,end:-1},P={top:1,center:0,bottom:-1},_=[0,0,0,255],C={billboard:!0,sizeScale:1,sizeUnits:"pixels",sizeMinPixels:0,sizeMaxPixels:Number.MAX_SAFE_INTEGER,background:!1,getBackgroundColor:{type:"accessor",value:[255,255,255,255]},getBorderColor:{type:"accessor",value:_},getBorderWidth:{type:"accessor",value:0},backgroundBorderRadius:{type:"object",value:0},backgroundPadding:{type:"array",value:[0,0,0,0]},characterSet:{type:"object",value:f.characterSet},fontFamily:f.fontFamily,fontWeight:f.fontWeight,lineHeight:1,outlineWidth:{type:"number",value:0,min:0},outlineColor:{type:"color",value:_},fontSettings:{type:"object",value:{},compare:1},wordBreak:"break-word",maxWidth:{type:"number",value:-1},getText:{type:"accessor",value:e=>e.text},getPosition:{type:"accessor",value:e=>e.position},getColor:{type:"accessor",value:_},getSize:{type:"accessor",value:32},getAngle:{type:"accessor",value:0},getTextAnchor:{type:"accessor",value:"middle"},getAlignmentBaseline:{type:"accessor",value:"center"},getPixelOffset:{type:"accessor",value:[0,0]},backgroundColor:{deprecatedFor:["background","getBackgroundColor"]}};class L extends o.A{constructor(){super(...arguments),this.getBoundingRect=(e,t)=>{let{size:[i,o]}=this.transformParagraph(e,t),{fontSize:n}=this.state.fontAtlasManager.props;i/=n,o/=n;let{getTextAnchor:s,getAlignmentBaseline:r}=this.props;return[(m["function"==typeof s?s(e,t):s]-1)*i/2,(P["function"==typeof r?r(e,t):r]-1)*o/2,i,o]},this.getIconOffsets=(e,t)=>{let{getTextAnchor:i,getAlignmentBaseline:o}=this.props,{x:n,y:s,rowWidth:r,size:[a,l]}=this.transformParagraph(e,t),c=m["function"==typeof i?i(e,t):i],u=P["function"==typeof o?o(e,t):o],d=n.length,p=Array(2*d),g=0;for(let e=0;e<d;e++){let t=(1-c)*(a-r[e])/2;p[g++]=(c-1)*a/2+t+n[e],p[g++]=(u-1)*l/2+s[e]}return p}}initializeState(){this.state={styleVersion:0,fontAtlasManager:new x},this.props.maxWidth>0&&n.A.once(1,"v8.9 breaking change: TextLayer maxWidth is now relative to text size")()}updateState(e){let{props:t,oldProps:i,changeFlags:o}=e;(o.dataChanged||o.updateTriggersChanged&&(o.updateTriggersChanged.all||o.updateTriggersChanged.getText))&&this._updateText(),(this._updateFontAtlas()||t.lineHeight!==i.lineHeight||t.wordBreak!==i.wordBreak||t.maxWidth!==i.maxWidth)&&this.setState({styleVersion:this.state.styleVersion+1})}getPickingInfo({info:e}){return e.object=e.index>=0?this.props.data[e.index]:null,e}_updateFontAtlas(){let{fontSettings:e,fontFamily:t,fontWeight:i}=this.props,{fontAtlasManager:o,characterSet:n}=this.state,s={...e,characterSet:n,fontFamily:t,fontWeight:i};if(!o.mapping)return o.setProps(s),!0;for(let e in s)if(s[e]!==o.props[e])return o.setProps(s),!0;return!1}_updateText(){let e;let{data:t,characterSet:i}=this.props,o=t.attributes?.getText,{getText:n}=this.props,r=t.startIndices,a="auto"===i&&new Set;if(o&&r){let{texts:i,characterCount:s}=function({value:e,length:t,stride:i,offset:o,startIndices:n,characterSet:s}){let r=e.BYTES_PER_ELEMENT,a=i?i/r:1,l=o?o/r:0,c=n[t]||Math.ceil((e.length-l)/a),u=s&&new Set,d=Array(t),p=e;if(a>1||l>0){p=new e.constructor(c);for(let t=0;t<c;t++)p[t]=e[t*a+l]}for(let e=0;e<t;e++){let t=n[e],i=n[e+1]||c,o=p.subarray(t,i);d[e]=String.fromCodePoint.apply(null,o),u&&o.forEach(u.add,u)}if(u)for(let e of u)s.add(String.fromCodePoint(e));return{texts:d,characterCount:c}}({...ArrayBuffer.isView(o)?{value:o}:o,length:t.length,startIndices:r,characterSet:a});e=s,n=(e,{index:t})=>i[t]}else{let{iterable:i,objectInfo:o}=(0,s.X)(t);for(let t of(r=[0],e=0,i)){o.index++;let i=Array.from(n(t,o)||"");a&&i.forEach(a.add,a),e+=i.length,r.push(e)}}this.setState({getText:n,startIndices:r,numInstances:e,characterSet:a||i})}transformParagraph(e,t){let{fontAtlasManager:i}=this.state,o=i.mapping,s=this.state.getText,{wordBreak:r,lineHeight:a,maxWidth:l}=this.props;return function(e,t,i,o,s){let r=Array.from(e),a=r.length,l=Array(a),c=Array(a),g=Array(a),f=("break-word"===i||"break-all"===i)&&isFinite(o)&&o>0,h=[0,0],v=[0,0],x=0,y=0,m=0;for(let e=0;e<=a;e++){let P=r[e];if(("\n"===P||e===a)&&(m=e),m>y){let e=f?function(e,t,i,o,n=0,s){void 0===s&&(s=e.length);let r=[];return"break-all"===t?p(e,n,s,i,o,r):function(e,t,i,o,n,s){let r=t,a=t,l=t,c=0;for(let u=t;u<i;u++)if(" "===e[u]?l=u+1:(" "===e[u+1]||u+1===i)&&(l=u+1),l>a){let t=d(e,a,l,n);c+t>o&&(r<a&&(s.push(a),r=a,c=0),t>o&&(t=p(e,a,l,o,n,s),r=s[s.length-1])),a=l,c+=t}return c}(e,n,s,i,o,r),r}(r,i,o,s,y,m):u;for(let i=0;i<=e.length;i++){let o=0===i?y:e[i-1],a=i<e.length?e[i]:m;!function(e,t,i,o,s,r){let a=0,l=0;for(let r=t;r<i;r++){let t=e[r],i=o[t];i?(l||(l=i.layoutHeight),s[r]=a+i.layoutWidth/2,a+=i.layoutWidth):(n.A.warn(`Missing character: ${t} (${t.codePointAt(0)})`)(),s[r]=a,a+=32)}r[0]=a,r[1]=l}(r,o,a,s,l,v);for(let e=o;e<a;e++){let t=r[e],i=s[t]?.layoutOffsetY||0;c[e]=x+v[1]/2+i,g[e]=v[0]}x+=v[1]*t,h[0]=Math.max(h[0],v[0])}y=m}"\n"===P&&(l[y]=0,c[y]=0,g[y]=0,y++)}return h[1]=x,{x:l,y:c,rowWidth:g,size:h}}(s(e,t)||"",a,r,l*i.props.fontSize,o)}renderLayers(){let{startIndices:e,numInstances:t,getText:i,fontAtlasManager:{scale:o,atlas:n,mapping:s},styleVersion:a}=this.state,{data:l,_dataDiff:c,getPosition:u,getColor:d,getSize:p,getAngle:g,getPixelOffset:h,getBackgroundColor:v,getBorderColor:x,getBorderWidth:m,backgroundBorderRadius:P,backgroundPadding:_,background:C,billboard:L,fontSettings:b,outlineWidth:S,outlineColor:A,sizeScale:w,sizeUnits:I,sizeMinPixels:M,sizeMaxPixels:z,transitions:E,updateTriggers:T}=this.props,R=this.getSubLayerClass("characters",r.A),O=this.getSubLayerClass("background",y.A);return[C&&new O({getFillColor:v,getLineColor:x,getLineWidth:m,borderRadius:P,padding:_,getPosition:u,getSize:p,getAngle:g,getPixelOffset:h,billboard:L,sizeScale:w,sizeUnits:I,sizeMinPixels:M,sizeMaxPixels:z,transitions:E&&{getPosition:E.getPosition,getAngle:E.getAngle,getSize:E.getSize,getFillColor:E.getBackgroundColor,getLineColor:E.getBorderColor,getLineWidth:E.getBorderWidth,getPixelOffset:E.getPixelOffset}},this.getSubLayerProps({id:"background",updateTriggers:{getPosition:T.getPosition,getAngle:T.getAngle,getSize:T.getSize,getFillColor:T.getBackgroundColor,getLineColor:T.getBorderColor,getLineWidth:T.getBorderWidth,getPixelOffset:T.getPixelOffset,getBoundingRect:{getText:T.getText,getTextAnchor:T.getTextAnchor,getAlignmentBaseline:T.getAlignmentBaseline,styleVersion:a}}}),{data:l.attributes&&l.attributes.background?{length:l.length,attributes:l.attributes.background}:l,_dataDiff:c,autoHighlight:!1,getBoundingRect:this.getBoundingRect}),new R({sdf:b.sdf,smoothing:Number.isFinite(b.smoothing)?b.smoothing:f.smoothing,outlineWidth:S/(b.radius||f.radius),outlineColor:A,iconAtlas:n,iconMapping:s,getPosition:u,getColor:d,getSize:p,getAngle:g,getPixelOffset:h,billboard:L,sizeScale:w*o,sizeUnits:I,sizeMinPixels:M*o,sizeMaxPixels:z*o,transitions:E&&{getPosition:E.getPosition,getAngle:E.getAngle,getColor:E.getColor,getSize:E.getSize,getPixelOffset:E.getPixelOffset}},this.getSubLayerProps({id:"characters",updateTriggers:{all:T.getText,getPosition:T.getPosition,getAngle:T.getAngle,getColor:T.getColor,getSize:T.getSize,getPixelOffset:T.getPixelOffset,getIconOffsets:{getTextAnchor:T.getTextAnchor,getAlignmentBaseline:T.getAlignmentBaseline,styleVersion:a}}}),{data:l,_dataDiff:c,startIndices:e,numInstances:t,getIconOffsets:this.getIconOffsets,getIcon:i})]}static set fontAtlasCacheLimit(e){n.A.assert(Number.isFinite(e)&&e>=3,"Invalid cache limit"),h=new g(e)}}L.defaultProps=C,L.layerName="TextLayer";let b=L},85036:(e,t,i)=>{i.d(t,{J:()=>o});function o({data:e,getIndex:t,dataRange:i,replace:o}){let{startRow:n=0,endRow:s=1/0}=i,r=e.length,a=r,l=r;for(let i=0;i<r;i++){let o=t(e[i]);if(a>i&&o>=n&&(a=i),o>=s){l=i;break}}let c=a,u=l-a!==o.length?e.slice(l):void 0;for(let t=0;t<o.length;t++)e[c++]=o[t];if(u){for(let t=0;t<u.length;t++)e[c++]=u[t];e.length=c}return{startRow:a,endRow:a+o.length}}},95952:(e,t,i)=>{i.d(t,{rJ:()=>o,wk:()=>M,Eg:()=>O,Mk:()=>I,Iy:()=>R,hY:()=>a,IC:()=>r,UD:()=>n});let o={CLOCKWISE:1,COUNTER_CLOCKWISE:-1};function n(e,t,i={}){return function(e,t={}){return Math.sign(r(e,t))}(e,i)!==t&&(function(e,t){let{start:i=0,end:o=e.length,size:n=2}=t,s=(o-i)/n,r=Math.floor(s/2);for(let t=0;t<r;++t){let o=i+t*n,r=i+(s-1-t)*n;for(let t=0;t<n;++t){let i=e[o+t];e[o+t]=e[r+t],e[r+t]=i}}}(e,i),!0)}let s={x:0,y:1,z:2};function r(e,t={}){let{start:i=0,end:o=e.length,plane:n="xy"}=t,a=t.size||2,l=0,c=s[n[0]],u=s[n[1]];for(let t=i,n=o-a;t<o;t+=a)l+=(e[t+c]-e[n+c])*(e[t+u]+e[n+u]),n=t;return l/2}function a(e,t,i=2,o,n="xy"){let s,r,v,x,P,C,L;let b=t&&t.length,S=b?t[0]*i:e.length,A=l(e,0,S,i,!0,o&&o[0],n),w=[];if(!A||A.next===A.prev)return w;if(b&&(A=function(e,t,i,o,n,s){let r,a,d,f,h;let v=[];for(r=0,a=t.length;r<a;r++)d=t[r]*o,f=r<a-1?t[r+1]*o:e.length,(h=l(e,d,f,o,!1,n&&n[r+1],s))===h.next&&(h.steiner=!0),v.push(function(e){let t=e,i=e;do(t.x<i.x||t.x===i.x&&t.y<i.y)&&(i=t),t=t.next;while(t!==e);return i}(h));for(v.sort(u),r=0;r<v.length;r++)i=function(e,t){let i=function(e,t){let i,o,n=t,s=e.x,r=e.y,a=-1/0;do{if(r<=n.y&&r>=n.next.y&&n.next.y!==n.y){let e=n.x+(r-n.y)*(n.next.x-n.x)/(n.next.y-n.y);if(e<=s&&e>a&&(a=e,i=n.x<n.next.x?n:n.next,e===s))return i}n=n.next}while(n!==t);if(!i)return null;let l=i,c=i.x,u=i.y,d=1/0;n=i;do{var f,h;s>=n.x&&n.x>=c&&s!==n.x&&p(r<u?s:a,r,c,u,r<u?a:s,r,n.x,n.y)&&(o=Math.abs(r-n.y)/(s-n.x),y(n,e)&&(o<d||o===d&&(n.x>i.x||n.x===i.x&&(f=i,h=n,0>g(f.prev,f,h.prev)&&0>g(h.next,f,f.next))))&&(i=n,d=o)),n=n.next}while(n!==l);return i}(e,t);if(!i)return t;let o=m(i,e);return c(o,o.next),c(i,i.next)}(v[r],i);return i}(e,t,A,i,o,n)),e.length>80*i){x=r=e[0],P=v=e[1];for(let t=i;t<S;t+=i)C=e[t],L=e[t+1],C<x&&(x=C),L<P&&(P=L),C>r&&(r=C),L>v&&(v=L);s=0!==(s=Math.max(r-x,v-P))?32767/s:0}return function e(t,i,o,n,s,r,a){let l,u;if(!t)return;!a&&r&&function(e,t,i,o){let n=e;do 0===n.z&&(n.z=d(n.x,n.y,t,i,o)),n.prevZ=n.prev,n.nextZ=n.next,n=n.next;while(n!==e);n.prevZ.nextZ=null,n.prevZ=null,function(e){let t,i,o,n,s,r,a,l;let c=1;do{for(n=e,e=null,l=null,o=0;n;){for(o++,r=n,s=0,i=0;i<c&&(s++,r=r.nextZ);i++);for(a=c;s>0||a>0&&r;)0!==s&&(0===a||!r||n.z<=r.z)?(t=n,n=n.nextZ,s--):(t=r,r=r.nextZ,a--),l?l.nextZ=t:e=t,t.prevZ=l,l=t;n=r}l.nextZ=null,c*=2}while(o>1)}(n)}(t,n,s,r);let v=t;for(;t.prev!==t.next;){if(l=t.prev,u=t.next,r?function(e,t,i,o){let n=e.prev,s=e.next;if(g(n,e,s)>=0)return!1;let r=n.x,a=e.x,l=s.x,c=n.y,u=e.y,f=s.y,h=r<a?r<l?r:l:a<l?a:l,v=c<u?c<f?c:f:u<f?u:f,x=r>a?r>l?r:l:a>l?a:l,y=c>u?c>f?c:f:u>f?u:f,m=d(h,v,t,i,o),P=d(x,y,t,i,o),_=e.prevZ,C=e.nextZ;for(;_&&_.z>=m&&C&&C.z<=P;){if(_.x>=h&&_.x<=x&&_.y>=v&&_.y<=y&&_!==n&&_!==s&&p(r,c,a,u,l,f,_.x,_.y)&&g(_.prev,_,_.next)>=0||(_=_.prevZ,C.x>=h&&C.x<=x&&C.y>=v&&C.y<=y&&C!==n&&C!==s&&p(r,c,a,u,l,f,C.x,C.y)&&g(C.prev,C,C.next)>=0))return!1;C=C.nextZ}for(;_&&_.z>=m;){if(_.x>=h&&_.x<=x&&_.y>=v&&_.y<=y&&_!==n&&_!==s&&p(r,c,a,u,l,f,_.x,_.y)&&g(_.prev,_,_.next)>=0)return!1;_=_.prevZ}for(;C&&C.z<=P;){if(C.x>=h&&C.x<=x&&C.y>=v&&C.y<=y&&C!==n&&C!==s&&p(r,c,a,u,l,f,C.x,C.y)&&g(C.prev,C,C.next)>=0)return!1;C=C.nextZ}return!0}(t,n,s,r):function(e){let t=e.prev,i=e.next;if(g(t,e,i)>=0)return!1;let o=t.x,n=e.x,s=i.x,r=t.y,a=e.y,l=i.y,c=o<n?o<s?o:s:n<s?n:s,u=r<a?r<l?r:l:a<l?a:l,d=o>n?o>s?o:s:n>s?n:s,f=r>a?r>l?r:l:a>l?a:l,h=i.next;for(;h!==t;){if(h.x>=c&&h.x<=d&&h.y>=u&&h.y<=f&&p(o,r,n,a,s,l,h.x,h.y)&&g(h.prev,h,h.next)>=0)return!1;h=h.next}return!0}(t)){i.push(l.i/o|0),i.push(t.i/o|0),i.push(u.i/o|0),_(t),t=u.next,v=u.next;continue}if((t=u)===v){a?1===a?e(t=function(e,t,i){let o=e;do{let n=o.prev,s=o.next.next;!f(n,s)&&h(n,o,o.next,s)&&y(n,s)&&y(s,n)&&(t.push(n.i/i|0),t.push(o.i/i|0),t.push(s.i/i|0),_(o),_(o.next),o=e=s),o=o.next}while(o!==e);return c(o)}(c(t),i,o),i,o,n,s,r,2):2===a&&function(t,i,o,n,s,r){let a=t;do{let t=a.next.next;for(;t!==a.prev;){var l,u;if(a.i!==t.i&&(l=a,u=t,l.next.i!==u.i&&l.prev.i!==u.i&&!function(e,t){let i=e;do{if(i.i!==e.i&&i.next.i!==e.i&&i.i!==t.i&&i.next.i!==t.i&&h(i,i.next,e,t))return!0;i=i.next}while(i!==e);return!1}(l,u)&&(y(l,u)&&y(u,l)&&function(e,t){let i=e,o=!1,n=(e.x+t.x)/2,s=(e.y+t.y)/2;do i.y>s!=i.next.y>s&&i.next.y!==i.y&&n<(i.next.x-i.x)*(s-i.y)/(i.next.y-i.y)+i.x&&(o=!o),i=i.next;while(i!==e);return o}(l,u)&&(g(l.prev,l,u.prev)||g(l,u.prev,u))||f(l,u)&&g(l.prev,l,l.next)>0&&g(u.prev,u,u.next)>0))){let l=m(a,t);a=c(a,a.next),l=c(l,l.next),e(a,i,o,n,s,r,0),e(l,i,o,n,s,r,0);return}t=t.next}a=a.next}while(a!==t)}(t,i,o,n,s,r):e(c(t),i,o,n,s,r,1);break}}}(A,w,i,x,P,s,0),w}function l(e,t,i,o,n,a,l){let c,u;void 0===a&&(a=r(e,{start:t,end:i,size:o,plane:l}));let d=s[l[0]],p=s[l[1]];if(n===a<0)for(c=t;c<i;c+=o)u=P(c,e[c+d],e[c+p],u);else for(c=i-o;c>=t;c-=o)u=P(c,e[c+d],e[c+p],u);return u&&f(u,u.next)&&(_(u),u=u.next),u}function c(e,t){let i;if(!e)return e;t||(t=e);let o=e;do if(i=!1,!o.steiner&&(f(o,o.next)||0===g(o.prev,o,o.next))){if(_(o),(o=t=o.prev)===o.next)break;i=!0}else o=o.next;while(i||o!==t);return t}function u(e,t){return e.x-t.x}function d(e,t,i,o,n){return(e=((e=((e=((e=((e=(e-i)*n|0)|e<<8)&0xff00ff)|e<<4)&0xf0f0f0f)|e<<2)&0x33333333)|e<<1)&0x55555555)|(t=((t=((t=((t=((t=(t-o)*n|0)|t<<8)&0xff00ff)|t<<4)&0xf0f0f0f)|t<<2)&0x33333333)|t<<1)&0x55555555)<<1}function p(e,t,i,o,n,s,r,a){return(n-r)*(t-a)>=(e-r)*(s-a)&&(e-r)*(o-a)>=(i-r)*(t-a)&&(i-r)*(s-a)>=(n-r)*(o-a)}function g(e,t,i){return(t.y-e.y)*(i.x-t.x)-(t.x-e.x)*(i.y-t.y)}function f(e,t){return e.x===t.x&&e.y===t.y}function h(e,t,i,o){let n=x(g(e,t,i)),s=x(g(e,t,o)),r=x(g(i,o,e)),a=x(g(i,o,t));return!!(n!==s&&r!==a||0===n&&v(e,i,t)||0===s&&v(e,o,t)||0===r&&v(i,e,o)||0===a&&v(i,t,o))}function v(e,t,i){return t.x<=Math.max(e.x,i.x)&&t.x>=Math.min(e.x,i.x)&&t.y<=Math.max(e.y,i.y)&&t.y>=Math.min(e.y,i.y)}function x(e){return e>0?1:e<0?-1:0}function y(e,t){return 0>g(e.prev,e,e.next)?g(e,t,e.next)>=0&&g(e,e.prev,t)>=0:0>g(e,t,e.prev)||0>g(e,e.next,t)}function m(e,t){let i=new C(e.i,e.x,e.y),o=new C(t.i,t.x,t.y),n=e.next,s=t.prev;return e.next=t,t.prev=e,i.next=n,n.prev=i,o.next=i,i.prev=o,s.next=o,o.prev=s,o}function P(e,t,i,o){let n=new C(e,t,i);return o?(n.next=o.next,n.prev=o,o.next.prev=n,o.next=n):(n.prev=n,n.next=n),n}function _(e){e.next.prev=e.prev,e.prev.next=e.next,e.prevZ&&(e.prevZ.nextZ=e.nextZ),e.nextZ&&(e.nextZ.prevZ=e.prevZ)}class C{constructor(e,t,i){this.prev=null,this.next=null,this.z=0,this.prevZ=null,this.nextZ=null,this.steiner=!1,this.i=e,this.x=t,this.y=i}}function L(e,t,i,o,n=[]){let s,r;if(8&i)s=(o[3]-e[1])/(t[1]-e[1]),r=3;else if(4&i)s=(o[1]-e[1])/(t[1]-e[1]),r=1;else if(2&i)s=(o[2]-e[0])/(t[0]-e[0]),r=2;else{if(!(1&i))return null;s=(o[0]-e[0])/(t[0]-e[0]),r=0}for(let i=0;i<e.length;i++)n[i]=(1&r)===i?o[r]:s*(t[i]-e[i])+e[i];return n}function b(e,t){let i=0;return e[0]<t[0]?i|=1:e[0]>t[2]&&(i|=2),e[1]<t[1]?i|=4:e[1]>t[3]&&(i|=8),i}function S(e,t){let i=t.length,o=e.length;if(o>0){let n=!0;for(let s=0;s<i;s++)if(e[o-i+s]!==t[s]){n=!1;break}if(n)return!1}for(let n=0;n<i;n++)e[o+n]=t[n];return!0}function A(e,t){let i=t.length;for(let o=0;o<i;o++)e[o]=t[o]}function w(e,t,i,o,n=[]){let s=o+t*i;for(let t=0;t<i;t++)n[t]=e[s+t];return n}function I(e,t){let i,o;let{size:n=2,broken:s=!1,gridResolution:r=10,gridOffset:a=[0,0],startIndex:l=0,endIndex:c=e.length}=t||{},u=(c-l)/n,d=[],p=[d],g=w(e,0,n,l),f=E(g,r,a,[]),h=[];S(d,g);for(let t=1;t<u;t++){for(o=b(i=w(e,t,n,l,i),f);o;){var v;L(g,i,o,f,h);let e=b(h,f);e&&(L(g,h,e,f,h),o=e),S(d,h),A(g,h),8&(v=o)?(f[1]+=r,f[3]+=r):4&v?(f[1]-=r,f[3]-=r):2&v?(f[0]+=r,f[2]+=r):1&v&&(f[0]-=r,f[2]-=r),s&&d.length>n&&(d=[],p.push(d),S(d,g)),o=b(i,f)}S(d,i),A(g,i)}return s?p:p[0]}function M(e,t=null,i){if(!e.length)return[];let{size:o=2,gridResolution:n=10,gridOffset:s=[0,0],edgeTypes:r=!1}=i||{},a=[],l=[{pos:e,types:r?Array(e.length/o).fill(1):null,holes:t||[]}],c=[[],[]],u=[];for(;l.length;){let{pos:e,types:t,holes:i}=l.shift();(function(e,t,i,o){let n=1/0,s=-1/0,r=1/0,a=-1/0;for(let o=0;o<i;o+=t){let t=e[o],i=e[o+1];n=t<n?t:n,s=t>s?t:s,r=i<r?i:r,a=i>a?i:a}o[0][0]=n,o[0][1]=r,o[1][0]=s,o[1][1]=a})(e,o,i[0]||e.length,c),u=E(c[0],n,s,u);let d=b(c[1],u);if(d){let n=z(e,t,o,0,i[0]||e.length,u,d),s={pos:n[0].pos,types:n[0].types,holes:[]},a={pos:n[1].pos,types:n[1].types,holes:[]};l.push(s,a);for(let l=0;l<i.length;l++)(n=z(e,t,o,i[l],i[l+1]||e.length,u,d))[0]&&(s.holes.push(s.pos.length),s.pos=T(s.pos,n[0].pos),r&&(s.types=T(s.types,n[0].types))),n[1]&&(a.holes.push(a.pos.length),a.pos=T(a.pos,n[1].pos),r&&(a.types=T(a.types,n[1].types)))}else{let o={positions:e};r&&(o.edgeTypes=t),i.length&&(o.holeIndices=i),a.push(o)}}return a}function z(e,t,i,o,n,s,r){let a,l,c;let u=(n-o)/i,d=[],p=[],g=[],f=[],h=[],v=w(e,u-1,i,o),x=Math.sign(8&r?v[1]-s[3]:v[0]-s[2]),y=t&&t[u-1],m=0,P=0;for(let n=0;n<u;n++)a=w(e,n,i,o,a),l=Math.sign(8&r?a[1]-s[3]:a[0]-s[2]),c=t&&t[o/i+n],l&&x&&x!==l&&(L(v,a,r,s,h),S(d,h)&&g.push(y),S(p,h)&&f.push(y)),l<=0?(S(d,a)&&g.push(c),m-=l):g.length&&(g[g.length-1]=0),l>=0?(S(p,a)&&f.push(c),P+=l):f.length&&(f[f.length-1]=0),A(v,a),x=l,y=c;return[m?{pos:d,types:t&&g}:null,P?{pos:p,types:t&&f}:null]}function E(e,t,i,o){let n=Math.floor((e[0]-i[0])/t)*t+i[0],s=Math.floor((e[1]-i[1])/t)*t+i[1];return o[0]=n,o[1]=s,o[2]=n+t,o[3]=s+t,o}function T(e,t){for(let i=0;i<t.length;i++)e.push(t[i]);return e}function R(e,t){let{size:i=2,startIndex:o=0,endIndex:n=e.length,normalize:s=!0}=t||{},r=e.slice(o,n);F(r,i,0,n-o);let a=I(r,{size:i,broken:!0,gridResolution:360,gridOffset:[-180,-180]});if(s)for(let e of a)k(e,i);return a}function O(e,t=null,i){let{size:o=2,normalize:n=!0,edgeTypes:s=!1}=i||{};t=t||[];let r=[],a=[],l=0,c=0;for(let n=0;n<=t.length;n++){let s=t[n]||e.length,u=c,d=function(e,t,i,o){let n=-1,s=-1;for(let r=i+1;r<o;r+=t){let t=Math.abs(e[r]);t>n&&(n=t,s=r-1)}return s}(e,o,l,s);for(let t=d;t<s;t++)r[c++]=e[t];for(let t=l;t<d;t++)r[c++]=e[t];F(r,o,u,c),function(e,t,i,o,n=85.051129){let s=e[i],r=e[o-t];if(Math.abs(s-r)>180){let o=w(e,0,t,i);o[0]+=360*Math.round((r-s)/360),S(e,o),o[1]=Math.sign(o[1])*n,S(e,o),o[0]=s,S(e,o)}}(r,o,u,c,i?.maxLatitude),l=s,a[n]=c}a.pop();let u=M(r,a,{size:o,gridResolution:360,gridOffset:[-180,-180],edgeTypes:s});if(n)for(let e of u)k(e.positions,o);return u}function F(e,t,i,o){let n,s=e[0];for(let r=i;r<o;r+=t){let t=(n=e[r])-s;(t>180||t<-180)&&(n-=360*Math.round(t/360)),e[r]=s=n}}function k(e,t){let i;let o=e.length/t;for(let n=0;n<o&&((i=e[n*t])+180)%360==0;n++);let n=-(360*Math.round(i/360));if(0!==n)for(let i=0;i<o;i++)e[i*t]+=n}}}]);