"use strict";(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[663],{5887:(t,e,i)=>{i.d(e,{A:()=>U});var r=i(19768),s=i(77002),n=i(48536),o=i(83210),a=i(39090),l=i(91358);let u=`\
out vec4 transform_output;
void main() {
  transform_output = vec4(0);
}`,h=`#version 300 es
${u}`;var d=i(91538);class c{device;model;transformFeedback;static defaultProps={...d.K.defaultProps,outputs:void 0,feedbackBuffers:void 0};static isSupported(t){return t?.info?.type==="webgl"}constructor(t,e=c.defaultProps){if(!c.isSupported(t))throw Error("BufferTransform not yet implemented on WebGPU");this.device=t,this.model=new d.K(this.device,{id:e.id||"buffer-transform-model",fs:e.fs||function(t){let{input:e,inputChannels:i,output:r}={};if(!e)return h;if(!i)throw Error("inputChannels");let s=function(t){switch(t){case 1:return"float";case 2:return"vec2";case 3:return"vec3";case 4:return"vec4";default:throw Error(`invalid channels: ${t}`)}}(i),n=function(t,e){switch(e){case 1:return`vec4(${t}, 0.0, 0.0, 1.0)`;case 2:return`vec4(${t}, 0.0, 1.0)`;case 3:return`vec4(${t}, 1.0)`;case 4:return t;default:throw Error(`invalid channels: ${e}`)}}(e,i);return`\
#version 300 es
in ${s} ${e};
out vec4 ${r};
void main() {
  ${r} = ${n};
}`}(),topology:e.topology||"point-list",varyings:e.outputs||e.varyings,...e}),this.transformFeedback=this.device.createTransformFeedback({layout:this.model.pipeline.shaderLayout,buffers:e.feedbackBuffers}),this.model.setTransformFeedback(this.transformFeedback),Object.seal(this)}destroy(){this.model&&this.model.destroy()}delete(){this.destroy()}run(t){t?.inputBuffers&&this.model.setAttributes(t.inputBuffers),t?.outputBuffers&&this.transformFeedback.setBuffers(t.outputBuffers);let e=this.device.beginRenderPass(t);this.model.draw(e),e.end()}getBuffer(t){return this.transformFeedback.getBuffer(t)}readAsync(t){let e=this.getBuffer(t);if(!e)throw Error("BufferTransform#getBuffer");if(e instanceof l.h)return e.readAsync();let{buffer:i,byteOffset:r=0,byteLength:s=i.byteLength}=e;return i.readAsync(r,s)}}function f(t,e=[],i=0){let r=Math.fround(t),s=t-r;return e[i]=r,e[i+1]=s,e}let p={name:"fp64arithmetic",vs:`\

uniform fp64arithmeticUniforms {
  uniform float ONE;
} fp64;

/*
About LUMA_FP64_CODE_ELIMINATION_WORKAROUND

The purpose of this workaround is to prevent shader compilers from
optimizing away necessary arithmetic operations by swapping their sequences
or transform the equation to some 'equivalent' form.

The method is to multiply an artifical variable, ONE, which will be known to
the compiler to be 1 only at runtime. The whole expression is then represented
as a polynomial with respective to ONE. In the coefficients of all terms, only one a
and one b should appear

err = (a + b) * ONE^6 - a * ONE^5 - (a + b) * ONE^4 + a * ONE^3 - b - (a + b) * ONE^2 + a * ONE
*/

// Divide float number to high and low floats to extend fraction bits
vec2 split(float a) {
  const float SPLIT = 4097.0;
  float t = a * SPLIT;
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float a_hi = t * fp64.ONE - (t - a);
  float a_lo = a * fp64.ONE - a_hi;
#else
  float a_hi = t - (t - a);
  float a_lo = a - a_hi;
#endif
  return vec2(a_hi, a_lo);
}

// Divide float number again when high float uses too many fraction bits
vec2 split2(vec2 a) {
  vec2 b = split(a.x);
  b.y += a.y;
  return b;
}

// Special sum operation when a > b
vec2 quickTwoSum(float a, float b) {
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float sum = (a + b) * fp64.ONE;
  float err = b - (sum - a) * fp64.ONE;
#else
  float sum = a + b;
  float err = b - (sum - a);
#endif
  return vec2(sum, err);
}

// General sum operation
vec2 twoSum(float a, float b) {
  float s = (a + b);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float v = (s * fp64.ONE - a) * fp64.ONE;
  float err = (a - (s - v) * fp64.ONE) * fp64.ONE * fp64.ONE * fp64.ONE + (b - v);
#else
  float v = s - a;
  float err = (a - (s - v)) + (b - v);
#endif
  return vec2(s, err);
}

vec2 twoSub(float a, float b) {
  float s = (a - b);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float v = (s * fp64.ONE - a) * fp64.ONE;
  float err = (a - (s - v) * fp64.ONE) * fp64.ONE * fp64.ONE * fp64.ONE - (b + v);
#else
  float v = s - a;
  float err = (a - (s - v)) - (b + v);
#endif
  return vec2(s, err);
}

vec2 twoSqr(float a) {
  float prod = a * a;
  vec2 a_fp64 = split(a);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float err = ((a_fp64.x * a_fp64.x - prod) * fp64.ONE + 2.0 * a_fp64.x *
    a_fp64.y * fp64.ONE * fp64.ONE) + a_fp64.y * a_fp64.y * fp64.ONE * fp64.ONE * fp64.ONE;
#else
  float err = ((a_fp64.x * a_fp64.x - prod) + 2.0 * a_fp64.x * a_fp64.y) + a_fp64.y * a_fp64.y;
#endif
  return vec2(prod, err);
}

vec2 twoProd(float a, float b) {
  float prod = a * b;
  vec2 a_fp64 = split(a);
  vec2 b_fp64 = split(b);
  float err = ((a_fp64.x * b_fp64.x - prod) + a_fp64.x * b_fp64.y +
    a_fp64.y * b_fp64.x) + a_fp64.y * b_fp64.y;
  return vec2(prod, err);
}

vec2 sum_fp64(vec2 a, vec2 b) {
  vec2 s, t;
  s = twoSum(a.x, b.x);
  t = twoSum(a.y, b.y);
  s.y += t.x;
  s = quickTwoSum(s.x, s.y);
  s.y += t.y;
  s = quickTwoSum(s.x, s.y);
  return s;
}

vec2 sub_fp64(vec2 a, vec2 b) {
  vec2 s, t;
  s = twoSub(a.x, b.x);
  t = twoSub(a.y, b.y);
  s.y += t.x;
  s = quickTwoSum(s.x, s.y);
  s.y += t.y;
  s = quickTwoSum(s.x, s.y);
  return s;
}

vec2 mul_fp64(vec2 a, vec2 b) {
  vec2 prod = twoProd(a.x, b.x);
  // y component is for the error
  prod.y += a.x * b.y;
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  prod = split2(prod);
#endif
  prod = quickTwoSum(prod.x, prod.y);
  prod.y += a.y * b.x;
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  prod = split2(prod);
#endif
  prod = quickTwoSum(prod.x, prod.y);
  return prod;
}

vec2 div_fp64(vec2 a, vec2 b) {
  float xn = 1.0 / b.x;
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  vec2 yn = mul_fp64(a, vec2(xn, 0));
#else
  vec2 yn = a * xn;
#endif
  float diff = (sub_fp64(a, mul_fp64(b, yn))).x;
  vec2 prod = twoProd(xn, diff);
  return sum_fp64(yn, prod);
}

vec2 sqrt_fp64(vec2 a) {
  if (a.x == 0.0 && a.y == 0.0) return vec2(0.0, 0.0);
  if (a.x < 0.0) return vec2(0.0 / 0.0, 0.0 / 0.0);

  float x = 1.0 / sqrt(a.x);
  float yn = a.x * x;
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  vec2 yn_sqr = twoSqr(yn) * fp64.ONE;
#else
  vec2 yn_sqr = twoSqr(yn);
#endif
  float diff = sub_fp64(a, yn_sqr).x;
  vec2 prod = twoProd(x * 0.5, diff);
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  return sum_fp64(split(yn), prod);
#else
  return sum_fp64(vec2(yn, 0.0), prod);
#endif
}
`,defaultUniforms:{ONE:1},uniformTypes:{ONE:"f32"},fp64ify:f,fp64LowPart:function(t){return t-Math.fround(t)},fp64ifyMatrix4:function(t){let e=new Float32Array(32);for(let i=0;i<4;++i)for(let r=0;r<4;++r){let s=4*i+r;f(t[4*r+i],e,2*s)}return e}};function g(t){let{source:e,target:i,start:r=0,size:s,getData:n}=t,o=t.end||i.length,a=e.length,l=o-r;if(a>l){i.set(e.subarray(0,l),r);return}if(i.set(e,r),!n)return;let u=a;for(;u<l;){let t=n(u,e);for(let e=0;e<s;e++)i[r+u]=t[e]||0,u++}}function m(t){switch(t){case 1:return"float";case 2:return"vec2";case 3:return"vec3";case 4:return"vec4";default:throw Error(`No defined attribute type for size "${t}"`)}}function b(t){switch(t){case 1:return"float32";case 2:return"float32x2";case 3:return"float32x3";case 4:return"float32x4";default:throw Error("invalid type size")}}function y(t){t.push(t.shift())}function v({device:t,source:e,target:i}){return(!i||i.byteLength<e.byteLength)&&(i?.destroy(),i=t.createBuffer({byteLength:e.byteLength,usage:e.usage})),i}function _({device:t,buffer:e,attribute:i,fromLength:r,toLength:s,fromStartIndices:n,getData:o=t=>t}){let a=i.doublePrecision&&i.value instanceof Float64Array?2:1,l=i.size*a,u=i.byteOffset,h=i.settings.bytesPerElement<4?u/i.settings.bytesPerElement*4:u,d=i.startIndices,c=n&&d,f=i.isConstant;if(!c&&e&&r>=s)return e;let p=i.value instanceof Float64Array?Float32Array:i.value.constructor,m=f?i.value:new p(i.getBuffer().readSyncWebGL(u,s*p.BYTES_PER_ELEMENT).buffer);if(i.settings.normalized&&!f){let t=o;o=(e,r)=>i.normalizeConstant(t(e,r))}let b=f?(t,e)=>o(m,e):(t,e)=>o(m.subarray(t+u,t+u+l),e),y=new Float32Array(e?e.readSyncWebGL(h,4*r).buffer:0),v=new Float32Array(s);return!function({source:t,target:e,size:i,getData:r,sourceStartIndices:s,targetStartIndices:n}){if(!s||!n)return g({source:t,target:e,size:i,getData:r});let o=0,a=0,l=r&&((t,e)=>r(t+a,e)),u=Math.min(s.length,n.length);for(let r=1;r<u;r++){let u=s[r]*i,h=n[r]*i;g({source:t.subarray(o,u),target:e,start:a,end:h,size:i,getData:l}),o=u,a=h}a<e.length&&g({source:[],target:e,start:a,size:i,getData:l})}({source:y,target:v,sourceStartIndices:n,targetStartIndices:d,size:l,getData:b}),(!e||e.byteLength<v.byteLength+h)&&(e?.destroy(),e=t.createBuffer({byteLength:v.byteLength+h,usage:35050})),e.write(v,h),e}var A=i(47236);class w{constructor({device:t,attribute:e,timeline:i}){this.buffers=[],this.currentLength=0,this.device=t,this.transition=new A.A(i),this.attribute=e,this.attributeInTransition=function(t){let{device:e,settings:i,value:s}=t,n=new r.A(e,i);return n.setData({value:s instanceof Float64Array?new Float64Array(0):new Float32Array(0),normalized:i.normalized}),n}(e),this.currentStartIndices=e.startIndices}get inProgress(){return this.transition.inProgress}start(t,e,i=1/0){this.settings=t,this.currentStartIndices=this.attribute.startIndices,this.currentLength=function(t,e){let{doublePrecision:i,settings:r,value:s,size:n}=t,o=i&&s instanceof Float64Array?2:1,a=0,{shaderAttributes:l}=t.settings;if(l)for(let t of Object.values(l))a=Math.max(a,t.vertexOffset??0);return(r.noAlloc?s.length:(e+a)*n)*o}(this.attribute,e),this.transition.start({...t,duration:i})}update(){let t=this.transition.update();return t&&this.onUpdate(),t}setBuffer(t){this.attributeInTransition.setData({buffer:t,normalized:this.attribute.settings.normalized,value:this.attributeInTransition.value})}cancel(){this.transition.cancel()}delete(){for(let t of(this.cancel(),this.buffers))t.destroy();this.buffers.length=0}}class C extends w{constructor({device:t,attribute:e,timeline:i}){super({device:t,attribute:e,timeline:i}),this.type="interpolation",this.transform=function(t,e){let i=e.size,r=m(i),s=b(i),n=e.getBufferLayout();return T(e)?new c(t,{vs:x,bufferLayout:[{name:"aFrom",byteStride:8*i,attributes:[{attribute:"aFrom",format:s,byteOffset:0},{attribute:"aFrom64Low",format:s,byteOffset:4*i}]},{name:"aTo",byteStride:8*i,attributes:[{attribute:"aTo",format:s,byteOffset:0},{attribute:"aTo64Low",format:s,byteOffset:4*i}]}],modules:[p,L],defines:{ATTRIBUTE_TYPE:r,ATTRIBUTE_SIZE:i},moduleSettings:{},varyings:["vCurrent","vCurrent64Low"],bufferMode:35980,disableWarnings:!0}):new c(t,{vs:P,bufferLayout:[{name:"aFrom",format:s},{name:"aTo",format:n.attributes[0].format}],modules:[L],defines:{ATTRIBUTE_TYPE:r},varyings:["vCurrent"],disableWarnings:!0})}(t,e)}start(t,e){let i=this.currentLength,r=this.currentStartIndices;if(super.start(t,e,t.duration),t.duration<=0){this.transition.cancel();return}let{buffers:s,attribute:n}=this;y(s),s[0]=_({device:this.device,buffer:s[0],attribute:n,fromLength:i,toLength:this.currentLength,fromStartIndices:r,getData:t.enter}),s[1]=v({device:this.device,source:s[0],target:s[1]}),this.setBuffer(s[1]);let{transform:o}=this,a=o.model,l=Math.floor(this.currentLength/n.size);T(n)&&(l/=2),a.setVertexCount(l),n.isConstant?(a.setAttributes({aFrom:s[0]}),a.setConstantAttributes({aTo:n.value})):a.setAttributes({aFrom:s[0],aTo:n.getBuffer()}),o.transformFeedback.setBuffers({vCurrent:s[1]})}onUpdate(){let{duration:t,easing:e}=this.settings,{time:i}=this.transition,r=i/t;e&&(r=e(r));let{model:s}=this.transform,n={time:r};s.shaderInputs.setProps({interpolation:n}),this.transform.run({discard:!0})}delete(){super.delete(),this.transform.destroy()}}let L={name:"interpolation",vs:`\
uniform interpolationUniforms {
  float time;
} interpolation;
`,uniformTypes:{time:"f32"}},P=`\
#version 300 es
#define SHADER_NAME interpolation-transition-vertex-shader

in ATTRIBUTE_TYPE aFrom;
in ATTRIBUTE_TYPE aTo;
out ATTRIBUTE_TYPE vCurrent;

void main(void) {
  vCurrent = mix(aFrom, aTo, interpolation.time);
  gl_Position = vec4(0.0);
}
`,x=`\
#version 300 es
#define SHADER_NAME interpolation-transition-vertex-shader

in ATTRIBUTE_TYPE aFrom;
in ATTRIBUTE_TYPE aFrom64Low;
in ATTRIBUTE_TYPE aTo;
in ATTRIBUTE_TYPE aTo64Low;
out ATTRIBUTE_TYPE vCurrent;
out ATTRIBUTE_TYPE vCurrent64Low;

vec2 mix_fp64(vec2 a, vec2 b, float x) {
  vec2 range = sub_fp64(b, a);
  return sum_fp64(a, mul_fp64(range, vec2(x, 0.0)));
}

void main(void) {
  for (int i=0; i<ATTRIBUTE_SIZE; i++) {
    vec2 value = mix_fp64(vec2(aFrom[i], aFrom64Low[i]), vec2(aTo[i], aTo64Low[i]), interpolation.time);
    vCurrent[i] = value.x;
    vCurrent64Low[i] = value.y;
  }
  gl_Position = vec4(0.0);
}
`;function T(t){return t.doublePrecision&&t.value instanceof Float64Array}class E extends w{constructor({device:t,attribute:e,timeline:i}){var r;super({device:t,attribute:e,timeline:i}),this.type="spring",this.texture=t.createTexture({data:new Uint8Array(4),format:"rgba8unorm",width:1,height:1}),this.framebuffer=(r=this.texture,t.createFramebuffer({id:"spring-transition-is-transitioning-framebuffer",width:1,height:1,colorAttachments:[r]})),this.transform=function(t,e){let i=m(e.size),r=b(e.size);return new c(t,{vs:S,fs:R,bufferLayout:[{name:"aPrev",format:r},{name:"aCur",format:r},{name:"aTo",format:e.getBufferLayout().attributes[0].format}],varyings:["vNext"],modules:[O],defines:{ATTRIBUTE_TYPE:i},parameters:{depthCompare:"always",blendColorOperation:"max",blendColorSrcFactor:"one",blendColorDstFactor:"one",blendAlphaOperation:"max",blendAlphaSrcFactor:"one",blendAlphaDstFactor:"one"}})}(t,e)}start(t,e){let i=this.currentLength,r=this.currentStartIndices;super.start(t,e);let{buffers:s,attribute:n}=this;for(let e=0;e<2;e++)s[e]=_({device:this.device,buffer:s[e],attribute:n,fromLength:i,toLength:this.currentLength,fromStartIndices:r,getData:t.enter});s[2]=v({device:this.device,source:s[0],target:s[2]}),this.setBuffer(s[1]);let{model:o}=this.transform;o.setVertexCount(Math.floor(this.currentLength/n.size)),n.isConstant?o.setConstantAttributes({aTo:n.value}):o.setAttributes({aTo:n.getBuffer()})}onUpdate(){let{buffers:t,transform:e,framebuffer:i,transition:r}=this,s=this.settings;e.model.setAttributes({aPrev:t[0],aCur:t[1]}),e.transformFeedback.setBuffers({vNext:t[2]});let n={stiffness:s.stiffness,damping:s.damping};e.model.shaderInputs.setProps({spring:n}),e.run({framebuffer:i,discard:!1,parameters:{viewport:[0,0,1,1]},clearColor:[0,0,0,0]}),y(t),this.setBuffer(t[1]),this.device.readPixelsToArrayWebGL(i)[0]>0||r.end()}delete(){super.delete(),this.transform.destroy(),this.texture.destroy(),this.framebuffer.destroy()}}let O={name:"spring",vs:`\
uniform springUniforms {
  float damping;
  float stiffness;
} spring;
`,uniformTypes:{damping:"f32",stiffness:"f32"}},S=`\
#version 300 es
#define SHADER_NAME spring-transition-vertex-shader

#define EPSILON 0.00001

in ATTRIBUTE_TYPE aPrev;
in ATTRIBUTE_TYPE aCur;
in ATTRIBUTE_TYPE aTo;
out ATTRIBUTE_TYPE vNext;
out float vIsTransitioningFlag;

ATTRIBUTE_TYPE getNextValue(ATTRIBUTE_TYPE cur, ATTRIBUTE_TYPE prev, ATTRIBUTE_TYPE dest) {
  ATTRIBUTE_TYPE velocity = cur - prev;
  ATTRIBUTE_TYPE delta = dest - cur;
  ATTRIBUTE_TYPE force = delta * spring.stiffness;
  ATTRIBUTE_TYPE resistance = velocity * spring.damping;
  return force - resistance + velocity + cur;
}

void main(void) {
  bool isTransitioning = length(aCur - aPrev) > EPSILON || length(aTo - aCur) > EPSILON;
  vIsTransitioningFlag = isTransitioning ? 1.0 : 0.0;

  vNext = getNextValue(aCur, aPrev, aTo);
  gl_Position = vec4(0, 0, 0, 1);
  gl_PointSize = 100.0;
}
`,R=`\
#version 300 es
#define SHADER_NAME spring-transition-is-transitioning-fragment-shader

in float vIsTransitioningFlag;

out vec4 fragColor;

void main(void) {
  if (vIsTransitioningFlag == 0.0) {
    discard;
  }
  fragColor = vec4(1.0);
}`,I={interpolation:C,spring:E};class B{constructor(t,{id:e,timeline:i}){if(!t)throw Error("AttributeTransitionManager is constructed without device");this.id=e,this.device=t,this.timeline=i,this.transitions={},this.needsRedraw=!1,this.numInstances=1}finalize(){for(let t in this.transitions)this._removeTransition(t)}update({attributes:t,transitions:e,numInstances:i}){for(let r in this.numInstances=i||1,t){let i=t[r],s=i.getTransitionSetting(e);s&&this._updateAttribute(r,i,s)}for(let i in this.transitions){let r=t[i];r&&r.getTransitionSetting(e)||this._removeTransition(i)}}hasAttribute(t){let e=this.transitions[t];return e&&e.inProgress}getAttributes(){let t={};for(let e in this.transitions){let i=this.transitions[e];i.inProgress&&(t[e]=i.attributeInTransition)}return t}run(){if(0===this.numInstances)return!1;for(let t in this.transitions)this.transitions[t].update()&&(this.needsRedraw=!0);let t=this.needsRedraw;return this.needsRedraw=!1,t}_removeTransition(t){this.transitions[t].delete(),delete this.transitions[t]}_updateAttribute(t,e,i){let r=this.transitions[t],n=!r||r.type!==i.type;if(n){r&&this._removeTransition(t);let o=I[i.type];o?this.transitions[t]=new o({attribute:e,timeline:this.timeline,device:this.device}):(s.A.error(`unsupported transition type '${i.type}'`)(),n=!1)}(n||e.needsRedraw())&&(this.needsRedraw=!0,this.transitions[t].start(i,this.numInstances))}}let N="attributeManager.invalidate";class U{constructor(t,{id:e="attribute-manager",stats:i,timeline:r}={}){this.mergeBoundsMemoized=(0,n.A)(o._Z),this.id=e,this.device=t,this.attributes={},this.updateTriggers={},this.needsRedraw=!0,this.userData={},this.stats=i,this.attributeTransitionManager=new B(t,{id:`${e}-transitions`,timeline:r}),Object.seal(this)}finalize(){for(let t in this.attributes)this.attributes[t].delete();this.attributeTransitionManager.finalize()}getNeedsRedraw(t={clearRedrawFlags:!1}){let e=this.needsRedraw;return this.needsRedraw=this.needsRedraw&&!t.clearRedrawFlags,e&&this.id}setNeedsRedraw(){this.needsRedraw=!0}add(t){this._add(t)}addInstanced(t){this._add(t,{stepMode:"instance"})}remove(t){for(let e of t)void 0!==this.attributes[e]&&(this.attributes[e].delete(),delete this.attributes[e])}invalidate(t,e){let i=this._invalidateTrigger(t,e);(0,a.A)(N,this,t,i)}invalidateAll(t){for(let e in this.attributes)this.attributes[e].setNeedsUpdate(e,t);(0,a.A)(N,this,"all")}update({data:t,numInstances:e,startIndices:i=null,transitions:r,props:n={},buffers:o={},context:l={}}){let u=!1;for(let r in(0,a.A)("attributeManager.updateStart",this),this.stats&&this.stats.get("Update Attributes").timeStart(),this.attributes){let a=this.attributes[r],h=a.settings.accessor;a.startIndices=i,a.numInstances=e,n[r]&&s.A.removed(`props.${r}`,`data.attributes.${r}`)(),a.setExternalBuffer(o[r])||a.setBinaryValue("string"==typeof h?o[h]:void 0,t.startIndices)||"string"==typeof h&&!o[h]&&a.setConstantValue(l,n[h])||a.needsUpdate()&&(u=!0,this._updateAttribute({attribute:a,numInstances:e,data:t,props:n,context:l})),this.needsRedraw=this.needsRedraw||a.needsRedraw()}u&&(0,a.A)("attributeManager.updateEnd",this,e),this.stats&&this.stats.get("Update Attributes").timeEnd(),this.attributeTransitionManager.update({attributes:this.attributes,numInstances:e,transitions:r})}updateTransition(){let{attributeTransitionManager:t}=this,e=t.run();return this.needsRedraw=this.needsRedraw||e,e}getAttributes(){return{...this.attributes,...this.attributeTransitionManager.getAttributes()}}getBounds(t){let e=t.map(t=>this.attributes[t]?.getBounds());return this.mergeBoundsMemoized(e)}getChangedAttributes(t={clearChangedFlags:!1}){let{attributes:e,attributeTransitionManager:i}=this,r={...i.getAttributes()};for(let s in e){let n=e[s];n.needsRedraw(t)&&!i.hasAttribute(s)&&(r[s]=n)}return r}getBufferLayouts(t){return Object.values(this.getAttributes()).map(e=>e.getBufferLayout(t))}_add(t,e){for(let i in t){let s=t[i],n={...s,id:i,size:s.isIndexed&&1||s.size||1,...e};this.attributes[i]=new r.A(this.device,n)}this._mapUpdateTriggersToAttributes()}_mapUpdateTriggersToAttributes(){let t={};for(let e in this.attributes)this.attributes[e].getUpdateTriggers().forEach(i=>{t[i]||(t[i]=[]),t[i].push(e)});this.updateTriggers=t}_invalidateTrigger(t,e){let{attributes:i,updateTriggers:r}=this,s=r[t];return s&&s.forEach(t=>{let r=i[t];r&&r.setNeedsUpdate(r.id,e)}),s}_updateAttribute(t){let{attribute:e,numInstances:i}=t;if((0,a.A)("attribute.updateStart",e),e.constant){e.setConstantValue(t.context,e.value);return}e.allocate(i)&&(0,a.A)("attribute.allocate",e,i),e.updateBuffer(t)&&(this.needsRedraw=!0,(0,a.A)("attribute.updateEnd",e,i))}}},19768:(t,e,i)=>{i.d(e,{A:()=>v});var r=i(91358),s=i(24247);let n=s.h1;function o(t,e,i){let r="webgpu"===i&&"uint8"===e.type?"unorm8":e.type;return{attribute:t,format:e.size>1?`${r}x${e.size}`:e.type,byteOffset:e.offset||0}}function a(t){return t.stride||t.size*t.bytesPerElement}var l=i(57066),u=i(83210),h=i(77002);function d(t,e){e.offset&&h.A.removed("shaderAttribute.offset","vertexOffset, elementOffset")();let i=a(t),r=(void 0!==e.vertexOffset?e.vertexOffset:t.vertexOffset||0)*i+(e.elementOffset||0)*t.bytesPerElement+(t.offset||0);return{...e,offset:r,stride:i}}class c{constructor(t,e,i){let r;this._buffer=null,this.device=t,this.id=e.id||"",this.size=e.size||1;let n=e.logicalType||e.type,o="float64"===n,{defaultValue:a}=e;a=Number.isFinite(a)?[a]:a||Array(this.size).fill(0),r=o?"float32":!n&&e.isIndexed?"uint32":n||"float32";let l=function(t){switch(t){case"float64":return Float64Array;case"uint8":case"unorm8":return Uint8ClampedArray;default:return(0,s.Ak)(t)}}(n||r);this.doublePrecision=o,o&&!1===e.fp64&&(l=Float32Array),this.value=null,this.settings={...e,defaultType:l,defaultValue:a,logicalType:n,type:r,normalized:r.includes("norm"),size:this.size,bytesPerElement:l.BYTES_PER_ELEMENT},this.state={...i,externalBuffer:null,bufferAccessor:this.settings,allocatedValue:null,numInstances:0,bounds:null,constant:!1}}get isConstant(){return this.state.constant}get buffer(){return this._buffer}get byteOffset(){let t=this.getAccessor();return t.vertexOffset?t.vertexOffset*a(t):0}get numInstances(){return this.state.numInstances}set numInstances(t){this.state.numInstances=t}delete(){this._buffer&&(this._buffer.delete(),this._buffer=null),l.A.release(this.state.allocatedValue)}getBuffer(){return this.state.constant?null:this.state.externalBuffer||this._buffer}getValue(t=this.id,e=null){let i={};if(this.state.constant){let r=this.value;if(e){let s=d(this.getAccessor(),e),n=s.offset/r.BYTES_PER_ELEMENT,o=s.size||this.size;i[t]=r.subarray(n,n+o)}else i[t]=r}else i[t]=this.getBuffer();return this.doublePrecision&&(this.value instanceof Float64Array?i[`${t}64Low`]=i[t]:i[`${t}64Low`]=new Float32Array(this.size)),i}_getBufferLayout(t=this.id,e=null){let i=this.getAccessor(),r=[],s={name:this.id,byteStride:a(i),attributes:r};if(this.doublePrecision){let s=function(t,e){let i=d(t,e);return{high:i,low:{...i,offset:i.offset+4*t.size}}}(i,e||{});r.push(o(t,{...i,...s.high},this.device.type),o(`${t}64Low`,{...i,...s.low},this.device.type))}else if(e){let s=d(i,e);r.push(o(t,{...i,...s},this.device.type))}else r.push(o(t,i,this.device.type));return s}setAccessor(t){this.state.bufferAccessor=t}getAccessor(){return this.state.bufferAccessor}getBounds(){if(this.state.bounds)return this.state.bounds;let t=null;if(this.state.constant&&this.value){let e=Array.from(this.value);t=[e,e]}else{let{value:e,numInstances:i,size:r}=this,s=i*r;if(e&&s&&e.length>=s){let i=Array(r).fill(1/0),n=Array(r).fill(-1/0);for(let t=0;t<s;)for(let s=0;s<r;s++){let r=e[t++];r<i[s]&&(i[s]=r),r>n[s]&&(n[s]=r)}t=[i,n]}}return this.state.bounds=t,t}setData(t){let e;let{state:i}=this;e=ArrayBuffer.isView(t)?{value:t}:t instanceof r.h?{buffer:t}:t;let s={...this.settings,...e};if(ArrayBuffer.isView(e.value)){if(!e.type){if(this.doublePrecision&&e.value instanceof Float64Array)s.type="float32";else{let t=n(e.value);s.type=s.normalized?t.replace("int","norm"):t}}s.bytesPerElement=e.value.BYTES_PER_ELEMENT,s.stride=a(s)}if(i.bounds=null,e.constant){let t=e.value;if(t=this._normalizeValue(t,[],0),this.settings.normalized&&(t=this.normalizeConstant(t)),!(!i.constant||!this._areValuesEqual(t,this.value)))return!1;i.externalBuffer=null,i.constant=!0,this.value=ArrayBuffer.isView(t)?t:new Float32Array(t)}else if(e.buffer){let t=e.buffer;i.externalBuffer=t,i.constant=!1,this.value=e.value||null}else if(e.value){this._checkExternalBuffer(e);let t=e.value;i.externalBuffer=null,i.constant=!1,this.value=t;let{buffer:r}=this,n=a(s),o=(s.vertexOffset||0)*n;if(this.doublePrecision&&t instanceof Float64Array&&(t=(0,u.cT)(t,s)),this.settings.isIndexed){let e=this.settings.defaultType;t.constructor!==e&&(t=new e(t))}let l=t.byteLength+o+2*n;(!r||r.byteLength<l)&&(r=this._createBuffer(l)),r.write(t,o)}return this.setAccessor(s),!0}updateSubBuffer(t={}){this.state.bounds=null;let e=this.value,{startOffset:i=0,endOffset:r}=t;this.buffer.write(this.doublePrecision&&e instanceof Float64Array?(0,u.cT)(e,{size:this.size,startIndex:i,endIndex:r}):e.subarray(i,r),i*e.BYTES_PER_ELEMENT+this.byteOffset)}allocate(t,e=!1){let{state:i}=this,r=i.allocatedValue,s=l.A.allocate(r,t+1,{size:this.size,type:this.settings.defaultType,copy:e});this.value=s;let{byteOffset:n}=this,{buffer:o}=this;return(!o||o.byteLength<s.byteLength+n)&&(o=this._createBuffer(s.byteLength+n),e&&r&&o.write(r instanceof Float64Array?(0,u.cT)(r,this):r,n)),i.allocatedValue=s,i.constant=!1,i.externalBuffer=null,this.setAccessor(this.settings),!0}_checkExternalBuffer(t){let{value:e}=t;if(!ArrayBuffer.isView(e))throw Error(`Attribute ${this.id} value is not TypedArray`);let i=this.settings.defaultType,r=!1;if(this.doublePrecision&&(r=e.BYTES_PER_ELEMENT<4),r)throw Error(`Attribute ${this.id} does not support ${e.constructor.name}`);e instanceof i||!this.settings.normalized||"normalized"in t||h.A.warn(`Attribute ${this.id} is normalized`)()}normalizeConstant(t){switch(this.settings.type){case"snorm8":return new Float32Array(t).map(t=>(t+128)/255*2-1);case"snorm16":return new Float32Array(t).map(t=>(t+32768)/65535*2-1);case"unorm8":return new Float32Array(t).map(t=>t/255);case"unorm16":return new Float32Array(t).map(t=>t/65535);default:return t}}_normalizeValue(t,e,i){let{defaultValue:r,size:s}=this.settings;if(Number.isFinite(t))return e[i]=t,e;if(!t){let t=s;for(;--t>=0;)e[i+t]=r[t];return e}switch(s){case 4:e[i+3]=Number.isFinite(t[3])?t[3]:r[3];case 3:e[i+2]=Number.isFinite(t[2])?t[2]:r[2];case 2:e[i+1]=Number.isFinite(t[1])?t[1]:r[1];case 1:e[i+0]=Number.isFinite(t[0])?t[0]:r[0];break;default:let n=s;for(;--n>=0;)e[i+n]=Number.isFinite(t[n])?t[n]:r[n]}return e}_areValuesEqual(t,e){if(!t||!e)return!1;let{size:i}=this;for(let r=0;r<i;r++)if(t[r]!==e[r])return!1;return!0}_createBuffer(t){this._buffer&&this._buffer.destroy();let{isIndexed:e,type:i}=this.settings;return this._buffer=this.device.createBuffer({...this._buffer?.props,id:this.id,usage:(e?r.h.INDEX:r.h.VERTEX)|r.h.COPY_DST,indexType:e?i:void 0,byteLength:t}),this._buffer}}var f=i(98922),p=i(98614),g=i(48886);let m=[],b=[[0,1/0]];var y=i(26862);class v extends c{constructor(t,e){super(t,e,{startIndices:null,lastExternalBuffer:null,binaryValue:null,binaryAccessor:null,needsUpdate:!0,needsRedraw:!1,layoutChanged:!1,updateRanges:b}),this.constant=!1,this.settings.update=e.update||(e.accessor?this._autoUpdater:void 0),Object.seal(this.settings),Object.seal(this.state),this._validateAttributeUpdaters()}get startIndices(){return this.state.startIndices}set startIndices(t){this.state.startIndices=t}needsUpdate(){return this.state.needsUpdate}needsRedraw({clearChangedFlags:t=!1}={}){let e=this.state.needsRedraw;return this.state.needsRedraw=e&&!t,e}layoutChanged(){return this.state.layoutChanged}setAccessor(t){var e,i;(e=this.state).layoutChanged||(e.layoutChanged=(i=this.getAccessor(),t.type!==i.type||t.size!==i.size||a(t)!==a(i)||(t.offset||0)!==(i.offset||0))),super.setAccessor(t)}getUpdateTriggers(){let{accessor:t}=this.settings;return[this.id].concat("function"!=typeof t&&t||[])}supportsTransition(){return!!this.settings.transition}getTransitionSetting(t){if(!t||!this.supportsTransition())return null;let{accessor:e}=this.settings,i=this.settings.transition,r=Array.isArray(e)?t[e.find(e=>t[e])]:t[e];return(0,y.K)(r,i)}setNeedsUpdate(t=this.id,e){if(this.state.needsUpdate=this.state.needsUpdate||t,this.setNeedsRedraw(t),e){let{startRow:t=0,endRow:i=1/0}=e;this.state.updateRanges=function(t,e){if(t===b||(e[0]<0&&(e[0]=0),e[0]>=e[1]))return t;let i=[],r=t.length,s=0;for(let n=0;n<r;n++){let r=t[n];r[1]<e[0]?(i.push(r),s=n+1):r[0]>e[1]?i.push(r):e=[Math.min(r[0],e[0]),Math.max(r[1],e[1])]}return i.splice(s,0,e),i}(this.state.updateRanges,[t,i])}else this.state.updateRanges=b}clearNeedsUpdate(){this.state.needsUpdate=!1,this.state.updateRanges=m}setNeedsRedraw(t=this.id){this.state.needsRedraw=this.state.needsRedraw||t}allocate(t){let{state:e,settings:i}=this;return!i.noAlloc&&!!i.update&&(super.allocate(t,e.updateRanges!==b),!0)}updateBuffer({numInstances:t,data:e,props:i,context:r}){if(!this.needsUpdate())return!1;let{state:{updateRanges:s},settings:{update:n,noAlloc:o}}=this,a=!0;if(n){for(let[o,a]of s)n.call(r,this,{data:e,startRow:o,endRow:a,props:i,numInstances:t});if(this.value){if(this.constant||!this.buffer||this.buffer.byteLength<this.value.byteLength+this.byteOffset)this.setData({value:this.value,constant:this.constant}),this.constant=!1;else for(let[e,i]of s){let r=Number.isFinite(e)?this.getVertexOffset(e):0,s=Number.isFinite(i)?this.getVertexOffset(i):o||!Number.isFinite(t)?this.value.length:t*this.size;super.updateSubBuffer({startOffset:r,endOffset:s})}}this._checkAttributeArray()}else a=!1;return this.clearNeedsUpdate(),this.setNeedsRedraw(),a}setConstantValue(t,e){let i="webgpu"===this.device.type;if(i||void 0===e||"function"==typeof e){if(i&&"function"!=typeof e){let t=this._normalizeValue(e,[],0);this._areValuesEqual(t,this.value)||this.setNeedsUpdate("WebGPU constant updated")}return!1}let r=this.settings.transform&&t?this.settings.transform.call(t,e):e;return this.setData({constant:!0,value:r})&&this.setNeedsRedraw(),this.clearNeedsUpdate(),!0}setExternalBuffer(t){let{state:e}=this;return t?(this.clearNeedsUpdate(),e.lastExternalBuffer===t||(e.lastExternalBuffer=t,this.setNeedsRedraw(),this.setData(t),!0)):(e.lastExternalBuffer=null,!1)}setBinaryValue(t,e=null){let{state:i,settings:r}=this;if(!t)return i.binaryValue=null,i.binaryAccessor=null,!1;if(r.noAlloc)return!1;if(i.binaryValue===t)return this.clearNeedsUpdate(),!0;if(i.binaryValue=t,this.setNeedsRedraw(),r.transform||e!==this.startIndices){ArrayBuffer.isView(t)&&(t={value:t});let s=t;(0,f.A)(ArrayBuffer.isView(s.value),`invalid ${r.accessor}`);let n=!!s.size&&s.size!==this.size;return i.binaryAccessor=(0,p.I)(s.value,{size:s.size||this.size,stride:s.stride,offset:s.offset,startIndices:e,nested:n}),!1}return this.clearNeedsUpdate(),this.setData(t),!0}getVertexOffset(t){let{startIndices:e}=this;return(e?t<e.length?e[t]:this.numInstances:t)*this.size}getValue(){let t=this.settings.shaderAttributes,e=super.getValue();if(!t)return e;for(let i in t)Object.assign(e,super.getValue(i,t[i]));return e}getBufferLayout(t){this.state.layoutChanged=!1;let e=this.settings.shaderAttributes,i=super._getBufferLayout(),{stepMode:r}=this.settings;if("dynamic"===r?i.stepMode=t?t.isInstanced?"instance":"vertex":"instance":i.stepMode=r??"vertex",!e)return i;for(let t in e){let r=super._getBufferLayout(t,e[t]);i.attributes.push(...r.attributes)}return i}_autoUpdater(t,{data:e,startRow:i,endRow:r,props:s,numInstances:n}){if(t.constant&&"webgpu"!==this.context.device.type)return;let{settings:o,state:a,value:l,size:u,startIndices:h}=t,{accessor:d,transform:c}=o,m=a.binaryAccessor||("function"==typeof d?d:s[d]);"function"!=typeof m&&"string"==typeof d&&(m=()=>s[d]),(0,f.A)("function"==typeof m,`accessor "${d}" is not a function`);let b=t.getVertexOffset(i),{iterable:y,objectInfo:v}=(0,p.X)(e,i,r);for(let e of y){v.index++;let i=m(e,v);if(c&&(i=c.call(this,i)),h){let e=(v.index<h.length-1?h[v.index+1]:n)-h[v.index];if(i&&Array.isArray(i[0])){let e=b;for(let r of i)t._normalizeValue(r,l,e),e+=u}else i&&i.length>u?l.set(i,b):(t._normalizeValue(i,v.target,0),(0,g.R)({target:l,source:v.target,start:b,count:e}));b+=e*u}else t._normalizeValue(i,l,b),b+=u}}_validateAttributeUpdaters(){let{settings:t}=this;if(!(t.noAlloc||"function"==typeof t.update))throw Error(`Attribute ${this.id} missing update or accessor`)}_checkAttributeArray(){let{value:t}=this,e=Math.min(4,this.size);if(t&&t.length>=e){let i=!0;switch(e){case 4:i=i&&Number.isFinite(t[3]);case 3:i=i&&Number.isFinite(t[2]);case 2:i=i&&Number.isFinite(t[1]);case 1:i=i&&Number.isFinite(t[0]);break;default:i=!1}if(!i)throw Error(`Illegal attribute generated for ${this.id}`)}}}},26862:(t,e,i)=>{i.d(e,{K:()=>s});let r={interpolation:{duration:0,easing:t=>t},spring:{stiffness:.05,damping:.5}};function s(t,e){if(!t)return null;Number.isFinite(t)&&(t={type:"interpolation",duration:t});let i=t.type||"interpolation";return{...r[i],...e,...t,type:i}}},24125:(t,e,i)=>{i.d(e,{A:()=>l});var r=i(98318),s=i(39090),n=i(48886),o=i(23464);class a extends r.A{get isComposite(){return!0}get isDrawable(){return!1}get isLoaded(){return super.isLoaded&&this.getSubLayers().every(t=>t.isLoaded)}getSubLayers(){return this.internalState&&this.internalState.subLayers||[]}initializeState(t){}setState(t){super.setState(t),this.setNeedsUpdate()}getPickingInfo({info:t}){let{object:e}=t;return e&&e.__source&&e.__source.parent&&e.__source.parent.id===this.id&&(t.object=e.__source.object,t.index=e.__source.index),t}filterSubLayer(t){return!0}shouldRenderSubLayer(t,e){return e&&e.length}getSubLayerClass(t,e){let{_subLayerProps:i}=this.props;return i&&i[t]&&i[t].type||e}getSubLayerRow(t,e,i){return t.__source={parent:this,object:e,index:i},t}getSubLayerAccessor(t){if("function"==typeof t){let e={index:-1,data:this.props.data,target:[]};return(i,r)=>i&&i.__source?(e.index=i.__source.index,t(i.__source.object,e)):t(i,r)}return t}getSubLayerProps(t={}){let{opacity:e,pickable:i,visible:r,parameters:s,getPolygonOffset:n,highlightedObjectIndex:a,autoHighlight:l,highlightColor:u,coordinateSystem:h,coordinateOrigin:d,wrapLongitude:c,positionFormat:f,modelMatrix:p,extensions:g,fetch:m,operation:b,_subLayerProps:y}=this.props,v={id:"",updateTriggers:{},opacity:e,pickable:i,visible:r,parameters:s,getPolygonOffset:n,highlightedObjectIndex:a,autoHighlight:l,highlightColor:u,coordinateSystem:h,coordinateOrigin:d,wrapLongitude:c,positionFormat:f,modelMatrix:p,extensions:g,fetch:m,operation:b},_=y&&t.id&&y[t.id],A=_&&_.updateTriggers,w=t.id||"sublayer";if(_){let e=this.props[o.fW],i=t.type?t.type._propTypes:{};for(let t in _){let r=i[t]||e[t];r&&"accessor"===r.type&&(_[t]=this.getSubLayerAccessor(_[t]))}}for(let e of(Object.assign(v,t,_),v.id=`${this.props.id}-${w}`,v.updateTriggers={all:this.props.updateTriggers?.all,...t.updateTriggers,...A},g)){let t=e.getSubLayerProps.call(this,e);t&&Object.assign(v,t,{updateTriggers:Object.assign(v.updateTriggers,t.updateTriggers)})}return v}_updateAutoHighlight(t){for(let e of this.getSubLayers())e.updateAutoHighlight(t)}_getAttributeManager(){return null}_postUpdate(t,e){let i=this.internalState.subLayers,r=!i||this.needsUpdate();if(r){let t=this.renderLayers();i=(0,n.B)(t,Boolean),this.internalState.subLayers=i}for(let t of((0,s.A)("compositeLayer.renderLayers",this,r,i),i))t.parent=this}}a.layerName="CompositeLayer";let l=a},98318:(t,e,i)=>{i.d(e,{A:()=>D});var r=i(91358),s=i(31248),n=i(60303),o=i(5887),a=i(26862),l=i(21108),u=i(47236);class h extends u.A{get value(){return this._value}_onUpdate(){let{time:t,settings:{fromValue:e,toValue:i,duration:r,easing:s}}=this,n=s(t/r);this._value=(0,l.Cc)(e,i,n)}}function d(t,e,i,r,s){let n=e-t;return(i-e)*s+-n*r+n+e}function c(t,e){if(Array.isArray(t)){let i=0;for(let r=0;r<t.length;r++){let s=t[r]-e[r];i+=s*s}return Math.sqrt(i)}return Math.abs(t-e)}class f extends u.A{get value(){return this._currValue}_onUpdate(){let{fromValue:t,toValue:e,damping:i,stiffness:r}=this.settings,{_prevValue:s=t,_currValue:n=t}=this,o=function(t,e,i,r,s){if(Array.isArray(i)){let n=[];for(let o=0;o<i.length;o++)n[o]=d(t[o],e[o],i[o],r,s);return n}return d(t,e,i,r,s)}(s,n,e,i,r),a=c(o,e),l=c(o,n);a<1e-5&&l<1e-5&&(o=e,this.end()),this._prevValue=n,this._currValue=o}}var p=i(77002);let g={interpolation:h,spring:f};class m{constructor(t){this.transitions=new Map,this.timeline=t}get active(){return this.transitions.size>0}add(t,e,i,r){let{transitions:s}=this;if(s.has(t)){let i=s.get(t),{value:r=i.settings.fromValue}=i;e=r,this.remove(t)}if(!(r=(0,a.K)(r)))return;let n=g[r.type];if(!n){p.A.error(`unsupported transition type '${r.type}'`)();return}let o=new n(this.timeline);o.start({...r,fromValue:e,toValue:i}),s.set(t,o)}remove(t){let{transitions:e}=this;e.has(t)&&(e.get(t).cancel(),e.delete(t))}update(){let t={};for(let[e,i]of this.transitions)i.update(),t[e]=i.value,i.inProgress||this.remove(e);return t}clear(){for(let t of this.transitions.keys())this.remove(t)}}var b=i(71711),y=i(23464),v=i(17663),_=i(39090),A=i(98922),w=i(48536),C=i(20565),L=i(5258),P=i(57066),x=i(30425),T=i(44650);class E extends T.A{constructor({attributeManager:t,layer:e}){super(e),this.attributeManager=t,this.needsRedraw=!0,this.needsUpdate=!0,this.subLayers=null,this.usesPickingColorCache=!1}get layer(){return this.component}_fetch(t,e){let i=this.layer,r=i?.props.fetch;return r?r(e,{propName:t,layer:i}):super._fetch(t,e)}_onResolve(t,e){let i=this.layer;if(i){let r=i.props.onDataLoad;"data"===t&&r&&r(e,{propName:t,layer:i})}}_onError(t,e){let i=this.layer;i&&i.raiseError(e,`loading ${t} of ${this.layer}`)}}var O=i(36706),S=i(3101);let R=Object.freeze([]),I=(0,w.A)(({oldViewport:t,viewport:e})=>t.equals(e)),B=new Uint8ClampedArray(0),N={data:{type:"data",value:R,async:!0},dataComparator:{type:"function",value:null,optional:!0},_dataDiff:{type:"function",value:t=>t&&t.__diff,optional:!0},dataTransform:{type:"function",value:null,optional:!0},onDataLoad:{type:"function",value:null,optional:!0},onError:{type:"function",value:null,optional:!0},fetch:{type:"function",value:(t,{propName:e,layer:i,loaders:r,loadOptions:s,signal:n})=>{let{resourceManager:o}=i.context;s=s||i.getLoadOptions(),r=r||i.props.loaders,n&&(s={...s,fetch:{...s?.fetch,signal:n}});let a=o.contains(t);return(a||s||(o.add({resourceId:t,data:(0,S.H)(t,r),persistent:!1}),a=!0),a)?o.subscribe({resourceId:t,onChange:t=>i.internalState?.reloadAsyncProp(e,t),consumerId:i.id,requestId:e}):(0,S.H)(t,r,s)}},updateTriggers:{},visible:!0,pickable:!1,opacity:{type:"number",min:0,max:1,value:1},operation:"draw",onHover:{type:"function",value:null,optional:!0},onClick:{type:"function",value:null,optional:!0},onDragStart:{type:"function",value:null,optional:!0},onDrag:{type:"function",value:null,optional:!0},onDragEnd:{type:"function",value:null,optional:!0},coordinateSystem:n.rf.DEFAULT,coordinateOrigin:{type:"array",value:[0,0,0],compare:!0},modelMatrix:{type:"array",value:null,compare:!0,optional:!0},wrapLongitude:!1,positionFormat:"XYZ",colorFormat:"RGBA",parameters:{type:"object",value:{},optional:!0,compare:2},loadOptions:{type:"object",value:null,optional:!0,ignore:!0},transitions:null,extensions:[],loaders:{type:"array",value:[],optional:!0,ignore:!0},getPolygonOffset:{type:"function",value:({layerIndex:t})=>[0,-(100*t)]},highlightedObjectIndex:null,autoHighlight:!1,highlightColor:{type:"accessor",value:[0,0,128,128]}};class U extends x.A{constructor(){super(...arguments),this.internalState=null,this.lifecycle=y.VD.NO_STATE,this.parent=null}static get componentName(){return Object.prototype.hasOwnProperty.call(this,"layerName")?this.layerName:""}get root(){let t=this;for(;t.parent;)t=t.parent;return t}toString(){let t=this.constructor.layerName||this.constructor.name;return`${t}({id: '${this.props.id}'})`}project(t){(0,A.A)(this.internalState);let e=this.internalState.viewport||this.context.viewport,i=(0,L.w)(t,{viewport:e,modelMatrix:this.props.modelMatrix,coordinateOrigin:this.props.coordinateOrigin,coordinateSystem:this.props.coordinateSystem}),[r,s,n]=(0,O.VJ)(i,e.pixelProjectionMatrix);return 2===t.length?[r,s]:[r,s,n]}unproject(t){return(0,A.A)(this.internalState),(this.internalState.viewport||this.context.viewport).unproject(t)}projectPosition(t,e){(0,A.A)(this.internalState);let i=this.internalState.viewport||this.context.viewport;return(0,L.R)(t,{viewport:i,modelMatrix:this.props.modelMatrix,coordinateOrigin:this.props.coordinateOrigin,coordinateSystem:this.props.coordinateSystem,...e})}get isComposite(){return!1}get isDrawable(){return!0}setState(t){this.setChangeFlags({stateChanged:!0}),Object.assign(this.state,t),this.setNeedsRedraw()}setNeedsRedraw(){this.internalState&&(this.internalState.needsRedraw=!0)}setNeedsUpdate(){this.internalState&&(this.context.layerManager.setNeedsUpdate(String(this)),this.internalState.needsUpdate=!0)}get isLoaded(){return!!this.internalState&&!this.internalState.isAsyncPropLoading()}get wrapLongitude(){return this.props.wrapLongitude}isPickable(){return this.props.pickable&&this.props.visible}getModels(){let t=this.state;return t&&(t.models||t.model&&[t.model])||[]}setShaderModuleProps(...t){for(let e of this.getModels())e.shaderInputs.setProps(...t)}getAttributeManager(){return this.internalState&&this.internalState.attributeManager}getCurrentLayer(){return this.internalState&&this.internalState.layer}getLoadOptions(){return this.props.loadOptions}use64bitPositions(){let{coordinateSystem:t}=this.props;return t===n.rf.DEFAULT||t===n.rf.LNGLAT||t===n.rf.CARTESIAN}onHover(t,e){return!!this.props.onHover&&(this.props.onHover(t,e)||!1)}onClick(t,e){return!!this.props.onClick&&(this.props.onClick(t,e)||!1)}nullPickingColor(){return[0,0,0]}encodePickingColor(t,e=[]){return e[0]=t+1&255,e[1]=t+1>>8&255,e[2]=t+1>>8>>8&255,e}decodePickingColor(t){(0,A.A)(t instanceof Uint8Array);let[e,i,r]=t;return e+256*i+65536*r-1}getNumInstances(){return Number.isFinite(this.props.numInstances)?this.props.numInstances:this.state&&void 0!==this.state.numInstances?this.state.numInstances:(0,v.U)(this.props.data)}getStartIndices(){return this.props.startIndices?this.props.startIndices:this.state&&this.state.startIndices?this.state.startIndices:null}getBounds(){return this.getAttributeManager()?.getBounds(["positions","instancePositions"])}getShaders(t){for(let e of(t=(0,C.n)(t,{disableWarnings:!0,modules:this.context.defaultShaderModules}),this.props.extensions))t=(0,C.n)(t,e.getShaders.call(this,e));return t}shouldUpdateState(t){return t.changeFlags.propsOrDataChanged}updateState(t){let e=this.getAttributeManager(),{dataChanged:i}=t.changeFlags;if(i&&e){if(Array.isArray(i))for(let t of i)e.invalidateAll(t);else e.invalidateAll()}if(e){let{props:i}=t,r=this.internalState.hasPickingBuffer,s=Number.isInteger(i.highlightedObjectIndex)||!!i.pickable||i.extensions.some(t=>t.getNeedsPickingBuffer.call(this,t));if(r!==s){this.internalState.hasPickingBuffer=s;let{pickingColors:t,instancePickingColors:i}=e.attributes,r=t||i;!r||(s&&r.constant&&(r.constant=!1,e.invalidate(r.id)),r.value||s||(r.constant=!0,r.value=[0,0,0]))}}}finalizeState(t){for(let t of this.getModels())t.destroy();let e=this.getAttributeManager();e&&e.finalize(),this.context&&this.context.resourceManager.unsubscribe({consumerId:this.id}),this.internalState&&(this.internalState.uniformTransitions.clear(),this.internalState.finalize())}draw(t){for(let e of this.getModels())e.draw(t.renderPass)}getPickingInfo({info:t,mode:e,sourceLayer:i}){let{index:r}=t;return r>=0&&Array.isArray(this.props.data)&&(t.object=this.props.data[r]),t}raiseError(t,e){e&&(t=Error(`${e}: ${t.message}`,{cause:t})),this.props.onError?.(t)||this.context?.onError?.(t,this)}getNeedsRedraw(t={clearRedrawFlags:!1}){return this._getNeedsRedraw(t)}needsUpdate(){return!!this.internalState&&(this.internalState.needsUpdate||this.hasUniformTransition()||this.shouldUpdateState(this._getUpdateParams()))}hasUniformTransition(){return this.internalState?.uniformTransitions.active||!1}activateViewport(t){if(!this.internalState)return;let e=this.internalState.viewport;this.internalState.viewport=t,e&&I({oldViewport:e,viewport:t})||(this.setChangeFlags({viewportChanged:!0}),this.isComposite?this.needsUpdate()&&this.setNeedsUpdate():this._update())}invalidateAttribute(t="all"){let e=this.getAttributeManager();e&&("all"===t?e.invalidateAll():e.invalidate(t))}updateAttributes(t){let e=!1;for(let i in t)t[i].layoutChanged()&&(e=!0);for(let i of this.getModels())this._setModelAttributes(i,t,e)}_updateAttributes(){let t=this.getAttributeManager();if(!t)return;let e=this.props,i=this.getNumInstances(),r=this.getStartIndices();t.update({data:e.data,numInstances:i,startIndices:r,props:e,transitions:e.transitions,buffers:e.data.attributes,context:this});let s=t.getChangedAttributes({clearChangedFlags:!0});this.updateAttributes(s)}_updateAttributeTransition(){let t=this.getAttributeManager();t&&t.updateTransition()}_updateUniformTransition(){let{uniformTransitions:t}=this.internalState;if(t.active){let e=t.update(),i=Object.create(this.props);for(let t in e)Object.defineProperty(i,t,{value:e[t]});return i}return this.props}calculateInstancePickingColors(t,{numInstances:e}){if(t.constant)return;let i=Math.floor(B.length/4);if(this.internalState.usesPickingColorCache=!0,i<e){e>0xffffff&&p.A.warn("Layer has too many data objects. Picking might not be able to distinguish all objects.")();let t=Math.floor((B=P.A.allocate(B,e,{size:4,copy:!0,maxCount:Math.max(e,0xffffff)})).length/4),r=[0,0,0];for(let e=i;e<t;e++)this.encodePickingColor(e,r),B[4*e+0]=r[0],B[4*e+1]=r[1],B[4*e+2]=r[2],B[4*e+3]=0}t.value=B.subarray(0,4*e)}_setModelAttributes(t,e,i=!1){if(!Object.keys(e).length)return;if(i){let i=this.getAttributeManager();t.setBufferLayout(i.getBufferLayouts(t)),e=i.getAttributes()}let s=t.userData?.excludeAttributes||{},n={},o={};for(let i in e){if(s[i])continue;let a=e[i].getValue();for(let s in a){let l=a[s];l instanceof r.h?e[i].settings.isIndexed?t.setIndexBuffer(l):n[s]=l:l&&(o[s]=l)}}t.setAttributes(n),t.setConstantAttributes(o)}disablePickingIndex(t){let e=this.props.data;if(!("attributes"in e)){this._disablePickingIndex(t);return}let{pickingColors:i,instancePickingColors:r}=this.getAttributeManager().attributes,s=i||r,n=s&&e.attributes&&e.attributes[s.id];if(n&&n.value){let i=n.value,r=this.encodePickingColor(t);for(let t=0;t<e.length;t++){let e=s.getVertexOffset(t);i[e]===r[0]&&i[e+1]===r[1]&&i[e+2]===r[2]&&this._disablePickingIndex(t)}}else this._disablePickingIndex(t)}_disablePickingIndex(t){let{pickingColors:e,instancePickingColors:i}=this.getAttributeManager().attributes,r=e||i;if(!r)return;let s=r.getVertexOffset(t),n=r.getVertexOffset(t+1);r.buffer.write(new Uint8Array(n-s),s)}restorePickingColors(){let{pickingColors:t,instancePickingColors:e}=this.getAttributeManager().attributes,i=t||e;i&&(this.internalState.usesPickingColorCache&&i.value.buffer!==B.buffer&&(i.value=B.subarray(0,i.value.length)),i.updateSubBuffer({startOffset:0}))}_initialize(){(0,A.A)(!this.internalState),(0,A.A)(Number.isFinite(this.props.coordinateSystem)),(0,_.A)("layer.initialize",this);let t=this._getAttributeManager();for(let e of(t&&t.addInstanced({instancePickingColors:{type:"uint8",size:4,noAlloc:!0,update:this.calculateInstancePickingColors}}),this.internalState=new E({attributeManager:t,layer:this}),this._clearChangeFlags(),this.state={},Object.defineProperty(this.state,"attributeManager",{get:()=>(p.A.deprecated("layer.state.attributeManager","layer.getAttributeManager()")(),t)}),this.internalState.uniformTransitions=new m(this.context.timeline),this.internalState.onAsyncPropUpdated=this._onAsyncPropUpdated.bind(this),this.internalState.setAsyncProps(this.props),this.initializeState(this.context),this.props.extensions))e.initializeState.call(this,this.context,e);this.setChangeFlags({dataChanged:"init",propsChanged:"init",viewportChanged:!0,extensionsChanged:!0}),this._update()}_transferState(t){(0,_.A)("layer.matched",this,this===t);let{state:e,internalState:i}=t;this!==t&&(this.internalState=i,this.state=e,this.internalState.setAsyncProps(this.props),this._diffProps(this.props,this.internalState.getOldProps()))}_update(){let t=this.needsUpdate();if((0,_.A)("layer.update",this,t),!t)return;let e=this.props,i=this.context,r=this.internalState,s=i.viewport,n=this._updateUniformTransition();r.propsInTransition=n,i.viewport=r.viewport||s,this.props=n;try{let t=this._getUpdateParams(),e=this.getModels();if(i.device)this.updateState(t);else try{this.updateState(t)}catch(t){}for(let e of this.props.extensions)e.updateState.call(this,t,e);this.setNeedsRedraw(),this._updateAttributes();let r=this.getModels()[0]!==e[0];this._postUpdate(t,r)}finally{i.viewport=s,this.props=e,this._clearChangeFlags(),r.needsUpdate=!1,r.resetOldProps()}}_finalize(){for(let t of((0,_.A)("layer.finalize",this),this.finalizeState(this.context),this.props.extensions))t.finalizeState.call(this,this.context,t)}_drawLayer({renderPass:t,shaderModuleProps:e=null,uniforms:i={},parameters:r={}}){this._updateAttributeTransition();let n=this.props,o=this.context;this.props=this.internalState.propsInTransition||n;try{e&&this.setShaderModuleProps(e);let{getPolygonOffset:n}=this.props,a=n&&n(i)||[0,0];for(let t of(o.device instanceof s.WebGLDevice&&o.device.setParametersWebGL({polygonOffset:a}),this.getModels()))"webgpu"===t.device.type?t.setParameters({...t.parameters,...r}):t.setParameters(r);if(o.device instanceof s.WebGLDevice)o.device.withParametersWebGL(r,()=>{let s={renderPass:t,shaderModuleProps:e,uniforms:i,parameters:r,context:o};for(let t of this.props.extensions)t.draw.call(this,s,t);this.draw(s)});else{let s={renderPass:t,shaderModuleProps:e,uniforms:i,parameters:r,context:o};for(let t of this.props.extensions)t.draw.call(this,s,t);this.draw(s)}}finally{this.props=n}}getChangeFlags(){return this.internalState?.changeFlags}setChangeFlags(t){if(!this.internalState)return;let{changeFlags:e}=this.internalState;for(let i in t)if(t[i]){let r=!1;if("dataChanged"===i){let s=t[i],n=e[i];s&&Array.isArray(n)&&(e.dataChanged=Array.isArray(s)?n.concat(s):s,r=!0)}e[i]||(e[i]=t[i],r=!0),r&&(0,_.A)("layer.changeFlag",this,i,t)}let i=!!(e.dataChanged||e.updateTriggersChanged||e.propsChanged||e.extensionsChanged);e.propsOrDataChanged=i,e.somethingChanged=i||e.viewportChanged||e.stateChanged}_clearChangeFlags(){this.internalState.changeFlags={dataChanged:!1,propsChanged:!1,updateTriggersChanged:!1,viewportChanged:!1,stateChanged:!1,extensionsChanged:!1,propsOrDataChanged:!1,somethingChanged:!1}}_diffProps(t,e){let i=(0,b.mg)(t,e);if(i.updateTriggersChanged)for(let t in i.updateTriggersChanged)i.updateTriggersChanged[t]&&this.invalidateAttribute(t);if(i.transitionsChanged)for(let r in i.transitionsChanged)this.internalState.uniformTransitions.add(r,e[r],t[r],t.transitions?.[r]);return this.setChangeFlags(i)}validateProps(){(0,b.zo)(this.props)}updateAutoHighlight(t){this.props.autoHighlight&&!Number.isInteger(this.props.highlightedObjectIndex)&&this._updateAutoHighlight(t)}_updateAutoHighlight(t){let e={highlightedObjectColor:t.picked?t.color:null},{highlightColor:i}=this.props;t.picked&&"function"==typeof i&&(e.highlightColor=i(t)),this.setShaderModuleProps({picking:e}),this.setNeedsRedraw()}_getAttributeManager(){let t=this.context;return new o.A(t.device,{id:this.props.id,stats:t.stats,timeline:t.timeline})}_postUpdate(t,e){let{props:i,oldProps:r}=t,s=this.state.model;s?.isInstanced&&s.setInstanceCount(this.getNumInstances());let{autoHighlight:n,highlightedObjectIndex:o,highlightColor:a}=i;if(e||r.autoHighlight!==n||r.highlightedObjectIndex!==o||r.highlightColor!==a){let t={};Array.isArray(a)&&(t.highlightColor=a),(e||r.autoHighlight!==n||o!==r.highlightedObjectIndex)&&(t.highlightedObjectColor=Number.isFinite(o)&&o>=0?this.encodePickingColor(o):null),this.setShaderModuleProps({picking:t})}}_getUpdateParams(){return{props:this.props,oldProps:this.internalState.getOldProps(),context:this.context,changeFlags:this.internalState.changeFlags}}_getNeedsRedraw(t){if(!this.internalState)return!1;let e=!1;e=this.internalState.needsRedraw&&this.id;let i=this.getAttributeManager(),r=!!i&&i.getNeedsRedraw(t);if(e=e||r)for(let t of this.props.extensions)t.onNeedsRedraw.call(this,t);return this.internalState.needsRedraw=this.internalState.needsRedraw&&!t.clearRedrawFlags,e}_onAsyncPropUpdated(){this._diffProps(this.props,this.internalState.getOldProps()),this.setNeedsUpdate()}}U.defaultProps=N,U.layerName="Layer";let D=U},44650:(t,e,i)=>{i.d(e,{A:()=>o});var r=i(98614),s=i(23464);let n=Object.freeze({});class o{constructor(t){this.component=t,this.asyncProps={},this.onAsyncPropUpdated=()=>{},this.oldProps=null,this.oldAsyncProps=null}finalize(){for(let t in this.asyncProps){let e=this.asyncProps[t];e&&e.type&&e.type.release&&e.type.release(e.resolvedValue,e.type,this.component)}this.asyncProps={},this.component=null,this.resetOldProps()}getOldProps(){return this.oldAsyncProps||this.oldProps||n}resetOldProps(){this.oldAsyncProps=null,this.oldProps=this.component?this.component.props:null}hasAsyncProp(t){return t in this.asyncProps}getAsyncProp(t){let e=this.asyncProps[t];return e&&e.resolvedValue}isAsyncPropLoading(t){if(t){let e=this.asyncProps[t];return!!(e&&e.pendingLoadCount>0&&e.pendingLoadCount!==e.resolvedLoadCount)}for(let t in this.asyncProps)if(this.isAsyncPropLoading(t))return!0;return!1}reloadAsyncProp(t,e){this._watchPromise(t,Promise.resolve(e))}setAsyncProps(t){this.component=t[s.r3]||this.component;let e=t[s.vf]||{},i=t[s.YN]||t,r=t[s.jA]||{};for(let t in e){let i=e[t];this._createAsyncPropData(t,r[t]),this._updateAsyncProp(t,i),e[t]=this.getAsyncProp(t)}for(let t in i){let e=i[t];this._createAsyncPropData(t,r[t]),this._updateAsyncProp(t,e)}}_fetch(t,e){return null}_onResolve(t,e){}_onError(t,e){}_updateAsyncProp(t,e){if(this._didAsyncInputValueChange(t,e)){if("string"==typeof e&&(e=this._fetch(t,e)),e instanceof Promise){this._watchPromise(t,e);return}if((0,r.Td)(e)){this._resolveAsyncIterable(t,e);return}this._setPropValue(t,e)}}_freezeAsyncOldProps(){if(!this.oldAsyncProps&&this.oldProps)for(let t in this.oldAsyncProps=Object.create(this.oldProps),this.asyncProps)Object.defineProperty(this.oldAsyncProps,t,{enumerable:!0,value:this.oldProps[t]})}_didAsyncInputValueChange(t,e){let i=this.asyncProps[t];return e!==i.resolvedValue&&e!==i.lastValue&&(i.lastValue=e,!0)}_setPropValue(t,e){this._freezeAsyncOldProps();let i=this.asyncProps[t];i&&(e=this._postProcessValue(i,e),i.resolvedValue=e,i.pendingLoadCount++,i.resolvedLoadCount=i.pendingLoadCount)}_setAsyncPropValue(t,e,i){let r=this.asyncProps[t];r&&i>=r.resolvedLoadCount&&void 0!==e&&(this._freezeAsyncOldProps(),r.resolvedValue=e,r.resolvedLoadCount=i,this.onAsyncPropUpdated(t,e))}_watchPromise(t,e){let i=this.asyncProps[t];if(i){i.pendingLoadCount++;let r=i.pendingLoadCount;e.then(e=>{this.component&&(e=this._postProcessValue(i,e),this._setAsyncPropValue(t,e,r),this._onResolve(t,e))}).catch(e=>{this._onError(t,e)})}}async _resolveAsyncIterable(t,e){if("data"!==t){this._setPropValue(t,e);return}let i=this.asyncProps[t];if(!i)return;i.pendingLoadCount++;let r=i.pendingLoadCount,s=[],n=0;for await(let i of e){if(!this.component)return;let{dataTransform:e}=this.component.props;Object.defineProperty(s=e?e(i,s):s.concat(i),"__diff",{enumerable:!1,value:[{startRow:n,endRow:s.length}]}),n=s.length,this._setAsyncPropValue(t,s,r)}this._onResolve(t,s)}_postProcessValue(t,e){let i=t.type;return i&&this.component&&(i.release&&i.release(t.resolvedValue,i,this.component),i.transform)?i.transform(e,i,this.component):e}_createAsyncPropData(t,e){if(!this.asyncProps[t]){let i=this.component&&this.component.props[s.fW];this.asyncProps[t]={type:i&&i[t],lastValue:null,resolvedValue:e,pendingLoadCount:0,resolvedLoadCount:0}}}}},30425:(t,e,i)=>{i.d(e,{A:()=>b});var r=i(23464),s=i(77002),n=i(98614),o=i(1443);let a={minFilter:"linear",mipmapFilter:"linear",magFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge"},l={};var u=i(34251);let h={boolean:{validate:(t,e)=>!0,equal:(t,e,i)=>!!t==!!e},number:{validate:(t,e)=>Number.isFinite(t)&&(!("max"in e)||t<=e.max)&&(!("min"in e)||t>=e.min)},color:{validate:(t,e)=>e.optional&&!t||c(t)&&(3===t.length||4===t.length),equal:(t,e,i)=>(0,u.b)(t,e,1)},accessor:{validate(t,e){let i=f(t);return"function"===i||i===f(e.value)},equal:(t,e,i)=>"function"==typeof e||(0,u.b)(t,e,1)},array:{validate:(t,e)=>e.optional&&!t||c(t),equal(t,e,i){let{compare:r}=i,s=Number.isInteger(r)?r:r?1:0;return r?(0,u.b)(t,e,s):t===e}},object:{equal(t,e,i){if(i.ignore)return!0;let{compare:r}=i,s=Number.isInteger(r)?r:r?1:0;return r?(0,u.b)(t,e,s):t===e}},function:{validate:(t,e)=>e.optional&&!t||"function"==typeof t,equal:(t,e,i)=>!i.compare&&!1!==i.ignore||t===e},data:{transform:(t,e,i)=>{if(!t)return t;let{dataTransform:r}=i.props;return r?r(t):"string"==typeof t.shape&&t.shape.endsWith("-table")&&Array.isArray(t.data)?t.data:t}},image:{transform:(t,e,i)=>{let r=i.context;return r&&r.device?function(t,e,i,r){if(i instanceof o.g)return i;i.constructor&&"Object"!==i.constructor.name&&(i={data:i});let s=null;i.compressed&&(s={minFilter:"linear",mipmapFilter:i.data.length>1?"nearest":"linear"});let{width:n,height:u}=i.data,h=e.createTexture({...i,sampler:{...a,...s,...r},mipLevels:e.getMipLevelCount(n,u)});return h.generateMipmapsWebGL(),l[h.id]=t,h}(i.id,r.device,t,{...e.parameters,...i.props.textureParameters}):null},release:(t,e,i)=>{!function(t,e){e&&e instanceof o.g&&l[e.id]===t&&(e.delete(),delete l[e.id])}(i.id,t)}}};function d(t,e){return"type"in e?{name:t,...h[e.type],...e}:"value"in e?{name:t,type:f(e.value),...e}:{name:t,type:"object",value:e}}function c(t){return Array.isArray(t)||ArrayBuffer.isView(t)}function f(t){return c(t)?"array":null===t?"null":typeof t}function p(t,e){return Object.prototype.hasOwnProperty.call(t,e)}let g=0;class m{constructor(...t){this.props=function(t,e){let i;for(let t=e.length-1;t>=0;t--){let r=e[t];"extensions"in r&&(i=r.extensions)}let o=Object.create(function t(e,i){var o;if(!(e instanceof b.constructor))return{};let a="_mergedDefaultProps";if(i)for(let t of i){let e=t.constructor;e&&(a+=`:${e.extensionName||e.name}`)}return p(e,o=a)&&e[o]||(e[a]=function(e,i){var o,a;if(!e.prototype)return null;let l=t(Object.getPrototypeOf(e)),u=function(t){let e={},i={},r={};for(let[s,n]of Object.entries(t)){let t=n?.deprecatedFor;if(t)r[s]=Array.isArray(t)?t:[t];else{let t=function(t,e){switch(f(e)){case"object":return d(t,e);case"array":return d(t,{type:"array",value:e,compare:!1});case"boolean":return d(t,{type:"boolean",value:e});case"number":return d(t,{type:"number",value:e});case"function":return d(t,{type:"function",value:e,compare:!0});default:return{name:t,type:"unknown",value:e}}}(s,n);e[s]=t,i[s]=t.value}}return{propTypes:e,defaultProps:i,deprecatedProps:r}}((a="defaultProps",p(o=e,a)&&o[a]||{})),h=Object.assign(Object.create(null),l,u.defaultProps),c=Object.assign(Object.create(null),l?.[r.fW],u.propTypes),g=Object.assign(Object.create(null),l?.[r.uH],u.deprecatedProps);for(let e of i){let i=t(e.constructor);i&&(Object.assign(h,i),Object.assign(c,i[r.fW]),Object.assign(g,i[r.uH]))}return Object.defineProperties(h,{id:{writable:!0,value:function(t){let e=t.componentName;return e||s.A.warn(`${t.name}.componentName not specified`)(),e||t.name}(e)}}),function(t,e){let i={},s={};for(let t in e){let o=e[t],{name:a,value:l}=o;o.async&&(i[a]=l,s[a]=function(t){return{enumerable:!0,set(e){"string"==typeof e||e instanceof Promise||(0,n.Td)(e)?this[r.YN][t]=e:this[r.vf][t]=e},get(){if(this[r.vf]){if(t in this[r.vf])return this[r.vf][t]||this[r.jA][t];if(t in this[r.YN]){let e=this[r.r3]&&this[r.r3].internalState;if(e&&e.hasAsyncProp(t))return e.getAsyncProp(t)||this[r.jA][t]}}return this[r.jA][t]}}}(a))}t[r.jA]=i,t[r.YN]={},Object.defineProperties(t,s)}(h,c),function(t,e){for(let i in e)Object.defineProperty(t,i,{enumerable:!1,set(t){let r=`${this.id}: ${i}`;for(let r of e[i])p(this,r)||(this[r]=t);s.A.deprecated(r,e[i].join("/"))()}})}(h,g),h[r.fW]=c,h[r.uH]=g,0!==i.length||p(e,"_propTypes")||(e._propTypes=c),h}(e,i||[]))}(t.constructor,i));o[r.r3]=t,o[r.YN]={},o[r.vf]={};for(let t=0;t<e.length;++t){let i=e[t];for(let t in i)o[t]=i[t]}return Object.freeze(o),o}(this,t),this.id=this.props.id,this.count=g++}clone(t){let{props:e}=this,i={};for(let t in e[r.jA])t in e[r.vf]?i[t]=e[r.vf][t]:t in e[r.YN]&&(i[t]=e[r.YN][t]);return new this.constructor({...e,...i,...t})}}m.componentName="Component",m.defaultProps={};let b=m},71711:(t,e,i)=>{i.d(e,{Me:()=>o,mg:()=>n,zo:()=>s});var r=i(23464);function s(t){let e=t[r.fW];for(let i in e){let r=e[i],{validate:s}=r;if(s&&!s(t[i],r))throw Error(`Invalid prop ${i}: ${t[i]}`)}}function n(t,e){let i=o({newProps:t,oldProps:e,propTypes:t[r.fW],ignoreProps:{data:null,updateTriggers:null,extensions:null,transitions:null}}),s=function(t,e){if(null===e)return"oldProps is null, initial diff";let i=!1,{dataComparator:r,_dataDiff:s}=t;return r?r(t.data,e.data)||(i="Data comparator detected a change"):t.data!==e.data&&(i="A new data container was supplied"),i&&s&&(i=s(t.data,e.data)||i),i}(t,e),n=!1;return s||(n=function(t,e){if(null===e||"all"in t.updateTriggers&&l(t,e,"all"))return{all:!0};let i={},r=!1;for(let s in t.updateTriggers)"all"!==s&&l(t,e,s)&&(i[s]=!0,r=!0);return!!r&&i}(t,e)),{dataChanged:s,propsChanged:i,updateTriggersChanged:n,extensionsChanged:function(t,e){if(null===e)return!0;let i=e.extensions,{extensions:r}=t;if(r===i)return!1;if(!i||!r||r.length!==i.length)return!0;for(let t=0;t<r.length;t++)if(!r[t].equals(i[t]))return!0;return!1}(t,e),transitionsChanged:function(t,e){if(!t.transitions)return!1;let i={},s=t[r.fW],n=!1;for(let r in t.transitions){let o=s[r],l=o&&o.type;("number"===l||"color"===l||"array"===l)&&a(t[r],e[r],o)&&(i[r]=!0,n=!0)}return!!n&&i}(t,e)}}function o({newProps:t,oldProps:e,ignoreProps:i={},propTypes:r={},triggerName:s="props"}){if(e===t)return!1;if("object"!=typeof t||null===t||"object"!=typeof e||null===e)return`${s} changed shallowly`;for(let n of Object.keys(t))if(!(n in i)){if(!(n in e))return`${s}.${n} added`;let i=a(t[n],e[n],r[n]);if(i)return`${s}.${n} ${i}`}for(let n of Object.keys(e))if(!(n in i)){if(!(n in t))return`${s}.${n} dropped`;if(!Object.hasOwnProperty.call(t,n)){let i=a(t[n],e[n],r[n]);if(i)return`${s}.${n} ${i}`}}return!1}function a(t,e,i){let r=i&&i.equal;return r&&!r(t,e,i)||!r&&(r=t&&e&&t.equals)&&!r.call(t,e)?"changed deeply":r||e===t?null:"changed shallowly"}function l(t,e,i){let r=t.updateTriggers[i];r=null==r?{}:r;let s=e.updateTriggers[i];return o({oldProps:s=null==s?{}:s,newProps:r,triggerName:i})}},95086:(t,e,i)=>{i.d(e,{A:()=>r});let r={name:"color",dependencies:[],source:`

struct ColorUniforms {
  opacity: f32,
};

var<private> color: ColorUniforms = ColorUniforms(1.0);
// TODO (kaapp) avoiding binding index collisions to handle layer opacity 
// requires some thought.
// @group(0) @binding(0) var<uniform> color: ColorUniforms;

@must_use
fn deckgl_premultiplied_alpha(fragColor: vec4<f32>) -> vec4<f32> {
    return vec4(fragColor.rgb * fragColor.a, fragColor.a); 
};
`,getUniforms:t=>({}),uniformTypes:{opacity:"f32"}}},65489:(t,e,i)=>{i.d(e,{A:()=>s});let r={props:{},uniforms:{},name:"picking",uniformTypes:{isActive:"f32",isAttribute:"f32",isHighlightActive:"f32",useFloatColors:"f32",highlightedObjectColor:"vec3<f32>",highlightColor:"vec4<f32>"},defaultUniforms:{isActive:!1,isAttribute:!1,isHighlightActive:!1,useFloatColors:!0,highlightedObjectColor:[0,0,0],highlightColor:[0,1,1,1]},vs:`\
uniform pickingUniforms {
  float isActive;
  float isAttribute;
  float isHighlightActive;
  float useFloatColors;
  vec3 highlightedObjectColor;
  vec4 highlightColor;
} picking;

out vec4 picking_vRGBcolor_Avalid;

// Normalize unsigned byte color to 0-1 range
vec3 picking_normalizeColor(vec3 color) {
  return picking.useFloatColors > 0.5 ? color : color / 255.0;
}

// Normalize unsigned byte color to 0-1 range
vec4 picking_normalizeColor(vec4 color) {
  return picking.useFloatColors > 0.5 ? color : color / 255.0;
}

bool picking_isColorZero(vec3 color) {
  return dot(color, vec3(1.0)) < 0.00001;
}

bool picking_isColorValid(vec3 color) {
  return dot(color, vec3(1.0)) > 0.00001;
}

// Check if this vertex is highlighted 
bool isVertexHighlighted(vec3 vertexColor) {
  vec3 highlightedObjectColor = picking_normalizeColor(picking.highlightedObjectColor);
  return
    bool(picking.isHighlightActive) && picking_isColorZero(abs(vertexColor - highlightedObjectColor));
}

// Set the current picking color
void picking_setPickingColor(vec3 pickingColor) {
  pickingColor = picking_normalizeColor(pickingColor);

  if (bool(picking.isActive)) {
    // Use alpha as the validity flag. If pickingColor is [0, 0, 0] fragment is non-pickable
    picking_vRGBcolor_Avalid.a = float(picking_isColorValid(pickingColor));

    if (!bool(picking.isAttribute)) {
      // Stores the picking color so that the fragment shader can render it during picking
      picking_vRGBcolor_Avalid.rgb = pickingColor;
    }
  } else {
    // Do the comparison with selected item color in vertex shader as it should mean fewer compares
    picking_vRGBcolor_Avalid.a = float(isVertexHighlighted(pickingColor));
  }
}

void picking_setPickingAttribute(float value) {
  if (bool(picking.isAttribute)) {
    picking_vRGBcolor_Avalid.r = value;
  }
}

void picking_setPickingAttribute(vec2 value) {
  if (bool(picking.isAttribute)) {
    picking_vRGBcolor_Avalid.rg = value;
  }
}

void picking_setPickingAttribute(vec3 value) {
  if (bool(picking.isAttribute)) {
    picking_vRGBcolor_Avalid.rgb = value;
  }
}
`,fs:`\
uniform pickingUniforms {
  float isActive;
  float isAttribute;
  float isHighlightActive;
  float useFloatColors;
  vec3 highlightedObjectColor;
  vec4 highlightColor;
} picking;

in vec4 picking_vRGBcolor_Avalid;

/*
 * Returns highlight color if this item is selected.
 */
vec4 picking_filterHighlightColor(vec4 color) {
  // If we are still picking, we don't highlight
  if (picking.isActive > 0.5) {
    return color;
  }

  bool selected = bool(picking_vRGBcolor_Avalid.a);

  if (selected) {
    // Blend in highlight color based on its alpha value
    float highLightAlpha = picking.highlightColor.a;
    float blendedAlpha = highLightAlpha + color.a * (1.0 - highLightAlpha);
    float highLightRatio = highLightAlpha / blendedAlpha;

    vec3 blendedRGB = mix(color.rgb, picking.highlightColor.rgb, highLightRatio);
    return vec4(blendedRGB, blendedAlpha);
  } else {
    return color;
  }
}

/*
 * Returns picking color if picking enabled else unmodified argument.
 */
vec4 picking_filterPickingColor(vec4 color) {
  if (bool(picking.isActive)) {
    if (picking_vRGBcolor_Avalid.a == 0.0) {
      discard;
    }
    return picking_vRGBcolor_Avalid;
  }
  return color;
}

/*
 * Returns picking color if picking is enabled if not
 * highlight color if this item is selected, otherwise unmodified argument.
 */
vec4 picking_filterColor(vec4 color) {
  vec4 highlightColor = picking_filterHighlightColor(color);
  return picking_filterPickingColor(highlightColor);
}
`,getUniforms:function(t={},e){let i={};if(void 0===t.highlightedObjectColor);else if(null===t.highlightedObjectColor)i.isHighlightActive=!1;else{i.isHighlightActive=!0;let e=t.highlightedObjectColor.slice(0,3);i.highlightedObjectColor=e}if(t.highlightColor){let e=Array.from(t.highlightColor,t=>t/255);Number.isFinite(e[3])||(e[3]=1),i.highlightColor=e}return void 0!==t.isActive&&(i.isActive=!!t.isActive,i.isAttribute=!!t.isAttribute),void 0!==t.useFloatColors&&(i.useFloatColors=!!t.useFloatColors),i}},s={...r,defaultUniforms:{...r.defaultUniforms,useFloatColors:!1},inject:{"vs:DECKGL_FILTER_GL_POSITION":`
    // for picking depth values
    picking_setPickingAttribute(position.z / position.w);
  `,"vs:DECKGL_FILTER_COLOR":`
  picking_setPickingColor(geometry.pickingColor);
  `,"fs:DECKGL_FILTER_COLOR":{order:99,injection:`
  // use highlight color if this fragment belongs to the selected object.
  color = picking_filterHighlightColor(color);

  // use picking color if rendering to picking FBO.
  color = picking_filterPickingColor(color);
    `}}}},5258:(t,e,i)=>{i.d(e,{R:()=>c,w:()=>d});var r=i(60303),s=i(55079),n=i(97831),o=i(44083),a=i(92514),l=i(36706);let u=[0,0,0];function h(t,e,i=!1){let r=e.projectPosition(t);if(i&&e instanceof n.A){let[i,s,n=0]=t,o=e.getDistanceScales([i,s]);r[2]=n*o.unitsPerMeter[2]}return r}function d(t,{viewport:e,modelMatrix:i,coordinateSystem:s,coordinateOrigin:n,offsetMode:a}){let[u,d,c=0]=t;switch(i&&([u,d,c]=o.Z0([],[u,d,c,1],i)),s){case r.rf.LNGLAT:return h([u,d,c],e,a);case r.rf.LNGLAT_OFFSETS:return h([u+n[0],d+n[1],c+(n[2]||0)],e,a);case r.rf.METER_OFFSETS:return h((0,l.dT)(n,[u,d,c]),e,a);case r.rf.CARTESIAN:default:return e.isGeospatial?[u+n[0],d+n[1],c+n[2]]:e.projectPosition([u,d,c])}}function c(t,e){let{viewport:i,coordinateSystem:n,coordinateOrigin:o,modelMatrix:l,fromCoordinateSystem:h,fromCoordinateOrigin:c}=function(t){let{viewport:e,modelMatrix:i,coordinateOrigin:s}=t,{coordinateSystem:n,fromCoordinateSystem:o,fromCoordinateOrigin:a}=t;return n===r.rf.DEFAULT&&(n=e.isGeospatial?r.rf.LNGLAT:r.rf.CARTESIAN),void 0===o&&(o=n),void 0===a&&(a=s),{viewport:e,coordinateSystem:n,coordinateOrigin:s,modelMatrix:i,fromCoordinateSystem:o,fromCoordinateOrigin:a}}(e),{autoOffset:f=!0}=e,{geospatialOrigin:p=u,shaderCoordinateOrigin:g=u,offsetMode:m=!1}=f?(0,s.o)(i,n,o):{},b=d(t,{viewport:i,modelMatrix:l,coordinateSystem:h,coordinateOrigin:c,offsetMode:m});if(m){let t=i.projectPosition(p||g);a.jb(b,b,t)}return b}},2854:(t,e,i)=>{i.d(e,{A:()=>o});var r=i(66078);let s=`\
// Define a structure to hold both the clip-space position and the common position.
struct ProjectResult {
  clipPosition: vec4<f32>,
  commonPosition: vec4<f32>,
};

// This function mimics the GLSL version with the 'out' parameter by returning both values.
fn project_position_to_clipspace_and_commonspace(
    position: vec3<f32>,
    position64Low: vec3<f32>,
    offset: vec3<f32>
) -> ProjectResult {
  // Compute the projected position.
  let projectedPosition: vec3<f32> = project_position_vec3_f64(position, position64Low);

  // Start with the provided offset.
  var finalOffset: vec3<f32> = offset;

  // Get whether a rotation is needed and the rotation matrix.
  let rotationResult = project_needs_rotation(projectedPosition);

  // If rotation is needed, update the offset.
  if (rotationResult.needsRotation) {
    finalOffset = rotationResult.transform * offset;
  }

  // Compute the common position.
  let commonPosition: vec4<f32> = vec4<f32>(projectedPosition + finalOffset, 1.0);

  // Convert to clip-space.
  let clipPosition: vec4<f32> = project_common_position_to_clipspace(commonPosition);

  return ProjectResult(clipPosition, commonPosition);
}

// A convenience overload that returns only the clip-space position.
fn project_position_to_clipspace(
    position: vec3<f32>,
    position64Low: vec3<f32>,
    offset: vec3<f32>
) -> vec4<f32> {
  return project_position_to_clipspace_and_commonspace(position, position64Low, offset).clipPosition;
}
`,n=`\
vec4 project_position_to_clipspace(
  vec3 position, vec3 position64Low, vec3 offset, out vec4 commonPosition
) {
  vec3 projectedPosition = project_position(position, position64Low);
  mat3 rotation;
  if (project_needs_rotation(projectedPosition, rotation)) {
    // offset is specified as ENU
    // when in globe projection, rotate offset so that the ground alighs with the surface of the globe
    offset = rotation * offset;
  }
  commonPosition = vec4(projectedPosition + offset, 1.0);
  return project_common_position_to_clipspace(commonPosition);
}

vec4 project_position_to_clipspace(
  vec3 position, vec3 position64Low, vec3 offset
) {
  vec4 commonPosition;
  return project_position_to_clipspace(position, position64Low, offset, commonPosition);
}
`,o={name:"project32",dependencies:[r.A],source:s,vs:n}},17663:(t,e,i)=>{i.d(e,{U:()=>r});function r(t){if(!(null!==t&&"object"==typeof t))throw Error("count(): argument not an object");if("function"==typeof t.count)return t.count();if(Number.isFinite(t.size))return t.size;if(Number.isFinite(t.length))return t.length;if(null!==t&&"object"==typeof t&&t.constructor===Object)return Object.keys(t).length;throw Error("count(): argument not a container")}},98614:(t,e,i)=>{i.d(e,{I:()=>a,Td:()=>o,X:()=>n});let r=[],s=[];function n(t,e=0,i=1/0){let o=r,a={index:-1,data:t,target:[]};return t?"function"==typeof t[Symbol.iterator]?o=t:t.length>0&&(s.length=t.length,o=s):o=r,(e>0||Number.isFinite(i))&&(o=(Array.isArray(o)?o:Array.from(o)).slice(e,i),a.index=e-1),{iterable:o,objectInfo:a}}function o(t){return t&&t[Symbol.asyncIterator]}function a(t,e){let{size:i,stride:r,offset:s,startIndices:n,nested:o}=e,a=t.BYTES_PER_ELEMENT,l=r?r/a:i,u=s?s/a:0,h=Math.floor((t.length-u)/l);return(e,{index:r,target:s})=>{let a;if(!n){let e=r*l+u;for(let r=0;r<i;r++)s[r]=t[e+r];return s}let d=n[r],c=n[r+1]||h;if(o){a=Array(c-d);for(let e=d;e<c;e++){let r=e*l+u;s=Array(i);for(let e=0;e<i;e++)s[e]=t[r+e];a[e-d]=s}}else if(l===i)a=t.subarray(d*i+u,c*i+u);else{a=new t.constructor((c-d)*i);let e=0;for(let r=d;r<c;r++){let s=r*l+u;for(let r=0;r<i;r++)a[e++]=t[s+r]}}return a}}},20565:(t,e,i)=>{i.d(e,{n:()=>r});function r(t,e){if(!e)return t;let i={...t,...e};if("defines"in e&&(i.defines={...t.defines,...e.defines}),"modules"in e&&(i.modules=(t.modules||[]).concat(e.modules),e.modules.some(t=>"project64"===t.name))){let t=i.modules.findIndex(t=>"project32"===t.name);t>=0&&i.modules.splice(t,1)}if("inject"in e){if(t.inject){let r={...t.inject};for(let t in e.inject)r[t]=(r[t]||"")+e.inject[t];i.inject=r}else i.inject=e.inject}return i}},53028:(t,e,i)=>{i.d(e,{A:()=>a});var r=i(98614),s=i(57066),n=i(98922),o=i(91358);class a{constructor(t){this.indexStarts=[0],this.vertexStarts=[0],this.vertexCount=0,this.instanceCount=0;let{attributes:e={}}=t;this.typedArrayManager=s.A,this.attributes={},this._attributeDefs=e,this.opts=t,this.updateGeometry(t)}updateGeometry(t){Object.assign(this.opts,t);let{data:e,buffers:i={},getGeometry:r,geometryBuffer:s,positionFormat:o,dataChanged:a,normalize:l=!0}=this.opts;if(this.data=e,this.getGeometry=r,this.positionSize=s&&s.size||("XY"===o?2:3),this.buffers=i,this.normalize=l,s&&((0,n.A)(e.startIndices),this.getGeometry=this.getGeometryFromBuffer(s),l||(i.vertexPositions=s)),this.geometryBuffer=i.vertexPositions,Array.isArray(a))for(let t of a)this._rebuildGeometry(t);else this._rebuildGeometry()}updatePartialGeometry({startRow:t,endRow:e}){this._rebuildGeometry({startRow:t,endRow:e})}getGeometryFromBuffer(t){let e=t.value||t;return ArrayBuffer.isView(e)?(0,r.I)(e,{size:this.positionSize,offset:t.offset,stride:t.stride,startIndices:this.data.startIndices}):null}_allocate(t,e){let{attributes:i,buffers:r,_attributeDefs:s,typedArrayManager:n}=this;for(let o in s)if(o in r)n.release(i[o]),i[o]=null;else{let r=s[o];r.copy=e,i[o]=n.allocate(i[o],t,r)}}_forEachGeometry(t,e,i){let{data:s,getGeometry:n}=this,{iterable:o,objectInfo:a}=(0,r.X)(s,e,i);for(let e of o)a.index++,t(n?n(e,a):null,a.index)}_rebuildGeometry(t){if(!this.data)return;let{indexStarts:e,vertexStarts:i,instanceCount:r}=this,{data:s,geometryBuffer:n}=this,{startRow:a=0,endRow:l=1/0}=t||{},u={};if(t||(e=[0],i=[0]),this.normalize||!n)this._forEachGeometry((t,e)=>{let r=t&&this.normalizeGeometry(t);u[e]=r,i[e+1]=i[e]+(r?this.getGeometrySize(r):0)},a,l),r=i[i.length-1];else if(r=(i=s.startIndices)[s.length]||0,ArrayBuffer.isView(n))r=r||n.length/this.positionSize;else if(n instanceof o.h){let t=4*this.positionSize;r=r||n.byteLength/t}else if(n.buffer){let t=n.stride||4*this.positionSize;r=r||n.buffer.byteLength/t}else if(n.value){let t=n.value,e=n.stride/t.BYTES_PER_ELEMENT||this.positionSize;r=r||t.length/e}this._allocate(r,!!t),this.indexStarts=e,this.vertexStarts=i,this.instanceCount=r;let h={};this._forEachGeometry((t,s)=>{let n=u[s]||t;h.vertexStart=i[s],h.indexStart=e[s];let o=s<i.length-1?i[s+1]:r;h.geometrySize=o-i[s],h.geometryIndex=s,this.updateGeometryAttributes(n,h)},a,l),this.vertexCount=e[e.length-1]}}},88912:(t,e,i)=>{i.d(e,{V:()=>s});var r=i(83349);class s{id;topology;vertexCount;indices;attributes;userData={};constructor(t){let{attributes:e={},indices:i=null,vertexCount:s=null}=t;for(let[s,n]of(this.id=t.id||(0,r.L)("geometry"),this.topology=t.topology,i&&(this.indices=ArrayBuffer.isView(i)?{value:i,size:1}:i),this.attributes={},Object.entries(e))){let t=ArrayBuffer.isView(n)?{value:n}:n;if(!ArrayBuffer.isView(t.value))throw Error(`${this._print(s)}: must be typed array or object with value as typed array`);if("POSITION"!==s&&"positions"!==s||t.size||(t.size=3),"indices"===s){if(this.indices)throw Error("Multiple indices detected");this.indices=t}else this.attributes[s]=t}this.indices&&void 0!==this.indices.isIndexed&&(this.indices=Object.assign({},this.indices),delete this.indices.isIndexed),this.vertexCount=s||this._calculateVertexCount(this.attributes,this.indices)}getVertexCount(){return this.vertexCount}getAttributes(){return this.indices?{indices:this.indices,...this.attributes}:this.attributes}_print(t){return`Geometry ${this.id} attribute ${t}`}_setAttributes(t,e){return this}_calculateVertexCount(t,e){if(e)return e.value.length;let i=1/0;for(let e of Object.values(t)){let{value:t,size:r,constant:s}=e;!s&&t&&void 0!==r&&r>=1&&(i=Math.min(i,t.length/r))}return i}}},91538:(t,e,i)=>{i.d(e,{K:()=>k});var r=i(53177),s=i(64578),n=i(91358);function o(t){return Array.isArray(t)?0===t.length||"number"==typeof t[0]:ArrayBuffer.isView(t)&&!(t instanceof DataView)}class a{name;uniforms={};modifiedUniforms={};modified=!0;bindingLayout={};needsRedraw="initialized";constructor(t){if(this.name=t?.name||"unnamed",t?.name&&t?.shaderLayout){let e=t?.shaderLayout.bindings?.find(e=>"uniform"===e.type&&e.name===t?.name);if(!e)throw Error(t?.name);for(let t of e.uniforms||[])this.bindingLayout[t.name]=t}}setUniforms(t){for(let[e,i]of Object.entries(t))this._setUniform(e,i),this.needsRedraw||this.setNeedsRedraw(`${this.name}.${e}=${i}`)}setNeedsRedraw(t){this.needsRedraw=this.needsRedraw||t}getAllUniforms(){return this.modifiedUniforms={},this.needsRedraw=!1,this.uniforms||{}}_setUniform(t,e){!function(t,e,i=16){if(t!==e||!o(t))return!1;if(o(e)&&t.length===e.length){for(let i=0;i<t.length;++i)if(e[i]!==t[i])return!1}return!0}(this.uniforms[t],e)&&(this.uniforms[t]=o(e)?e.slice():e,this.modifiedUniforms[t]=!0,this.modified=!0)}}var l=i(24247),u=i(61478),h=i(87439);class d{layout={};byteLength;constructor(t,e={}){let i=0;for(let[r,s]of Object.entries(t)){let{type:t,components:n}=(0,u.k0)(s),o=n*(e?.[r]??1),a=i=(0,l.JP)(i,o);i+=o,this.layout[r]={type:t,size:o,offset:a}}let r=4*(i+=(4-i%4)%4);this.byteLength=Math.max(r,1024)}getData(t){let e=(0,h.o)(this.byteLength),i={i32:new Int32Array(e),u32:new Uint32Array(e),f32:new Float32Array(e),f16:new Uint16Array(e)};for(let[e,r]of Object.entries(t)){let t=this.layout[e];if(!t){s.R.warn(`Supplied uniform value ${e} not present in uniform block layout`)();continue}let{type:n,size:a,offset:l}=t,u=i[n];if(1===a){if("number"!=typeof r&&"boolean"!=typeof r){s.R.warn(`Supplied value for single component uniform ${e} is not a number: ${r}`)();continue}u[l]=Number(r)}else{if(!o(r)){s.R.warn(`Supplied value for multi component / array uniform ${e} is not a numeric array: ${r}`)();continue}u.set(r,l)}}return new Uint8Array(e,0,this.byteLength)}has(t){return!!this.layout[t]}get(t){return this.layout[t]}}class c{uniformBlocks=new Map;uniformBufferLayouts=new Map;uniformBuffers=new Map;constructor(t){for(let[e,i]of Object.entries(t)){let t=new d(i.uniformTypes??{},i.uniformSizes??{});this.uniformBufferLayouts.set(e,t);let r=new a({name:e});r.setUniforms(i.defaultUniforms||{}),this.uniformBlocks.set(e,r)}}destroy(){for(let t of this.uniformBuffers.values())t.destroy()}setUniforms(t){for(let[e,i]of Object.entries(t))this.uniformBlocks.get(e)?.setUniforms(i);this.updateUniformBuffers()}getUniformBufferByteLength(t){return this.uniformBufferLayouts.get(t)?.byteLength||0}getUniformBufferData(t){let e=this.uniformBlocks.get(t)?.getAllUniforms()||{};return this.uniformBufferLayouts.get(t)?.getData(e)}createUniformBuffer(t,e,i){i&&this.setUniforms(i);let r=this.getUniformBufferByteLength(e),s=t.createBuffer({usage:n.h.UNIFORM|n.h.COPY_DST,byteLength:r}),o=this.getUniformBufferData(e);return s.write(o),s}getManagedUniformBuffer(t,e){if(!this.uniformBuffers.get(e)){let i=this.getUniformBufferByteLength(e),r=t.createBuffer({usage:n.h.UNIFORM|n.h.COPY_DST,byteLength:i});this.uniformBuffers.set(e,r)}return this.uniformBuffers.get(e)}updateUniformBuffers(){let t=!1;for(let e of this.uniformBlocks.keys()){let i=this.updateUniformBuffer(e);t||=i}return t&&s.R.log(3,`UniformStore.updateUniformBuffers(): ${t}`)(),t}updateUniformBuffer(t){let e=this.uniformBlocks.get(t),i=this.uniformBuffers.get(t),r=!1;if(i&&e?.needsRedraw){r||=e.needsRedraw;let n=this.getUniformBufferData(t);i=this.uniformBuffers.get(t),i?.write(n);let o=this.uniformBlocks.get(t)?.getAllUniforms();s.R.log(4,`Writing to uniform buffer ${String(t)}`,n,o)()}return r}}var f=i(86487),p=i(1443),g=i(20),m=i(30628),b=i(97174),y=i(52861);function v(t){return t?.format?`${t.name}<${t.format.name}>`:t.name}var _=i(12812),A=i(83349);class w{id;userData={};topology;bufferLayout=[];vertexCount;indices;attributes;constructor(t){if(this.id=t.id||(0,A.L)("geometry"),this.topology=t.topology,this.indices=t.indices||null,this.attributes=t.attributes,this.vertexCount=t.vertexCount,this.bufferLayout=t.bufferLayout||[],this.indices&&!(this.indices.usage&n.h.INDEX))throw Error("Index buffer must have INDEX usage")}destroy(){for(let t of(this.indices?.destroy(),Object.values(this.attributes)))t.destroy()}getVertexCount(){return this.vertexCount}getAttributes(){return this.attributes}getIndexes(){return this.indices||null}_calculateVertexCount(t){return t.byteLength/12}}var C=i(14856);class L extends C.F{get[Symbol.toStringTag](){return"ComputePipeline"}hash="";shaderLayout;constructor(t,e){super(t,e,L.defaultProps),this.shaderLayout=e.shaderLayout}static defaultProps={...C.F.defaultProps,shader:void 0,entryPoint:void 0,constants:{},shaderLayout:void 0}}class P{static defaultProps={...r.r.defaultProps};static getDefaultPipelineFactory(t){return t._lumaData.defaultPipelineFactory=t._lumaData.defaultPipelineFactory||new P(t),t._lumaData.defaultPipelineFactory}device;cachingEnabled;destroyPolicy;debug;_hashCounter=0;_hashes={};_renderPipelineCache={};_computePipelineCache={};get[Symbol.toStringTag](){return"PipelineFactory"}toString(){return`PipelineFactory(${this.device.id})`}constructor(t){this.device=t,this.cachingEnabled=t.props._cachePipelines,this.destroyPolicy=t.props._cacheDestroyPolicy,this.debug=t.props.debugFactories}createRenderPipeline(t){if(!this.cachingEnabled)return this.device.createRenderPipeline(t);let e={...r.r.defaultProps,...t},i=this._renderPipelineCache,n=this._hashRenderPipeline(e),o=i[n]?.pipeline;return o?(i[n].useCount++,this.debug&&s.R.log(3,`${this}: ${i[n].pipeline} reused, count=${i[n].useCount}, (id=${t.id})`)()):((o=this.device.createRenderPipeline({...e,id:e.id?`${e.id}-cached`:(0,A.L)("unnamed-cached")})).hash=n,i[n]={pipeline:o,useCount:1},this.debug&&s.R.log(3,`${this}: ${o} created, count=${i[n].useCount}`)()),o}createComputePipeline(t){if(!this.cachingEnabled)return this.device.createComputePipeline(t);let e={...L.defaultProps,...t},i=this._computePipelineCache,r=this._hashComputePipeline(e),n=i[r]?.pipeline;return n?(i[r].useCount++,this.debug&&s.R.log(3,`${this}: ${i[r].pipeline} reused, count=${i[r].useCount}, (id=${t.id})`)()):((n=this.device.createComputePipeline({...e,id:e.id?`${e.id}-cached`:void 0})).hash=r,i[r]={pipeline:n,useCount:1},this.debug&&s.R.log(3,`${this}: ${n} created, count=${i[r].useCount}`)()),n}release(t){if(!this.cachingEnabled){t.destroy();return}let e=this._getCache(t),i=t.hash;e[i].useCount--,0===e[i].useCount?(this._destroyPipeline(t),this.debug&&s.R.log(3,`${this}: ${t} released and destroyed`)()):e[i].useCount<0?(s.R.error(`${this}: ${t} released, useCount < 0, resetting`)(),e[i].useCount=0):this.debug&&s.R.log(3,`${this}: ${t} released, count=${e[i].useCount}`)()}_destroyPipeline(t){let e=this._getCache(t);switch(this.destroyPolicy){case"never":return!1;case"unused":return delete e[t.hash],t.destroy(),!0}}_getCache(t){let e;if(t instanceof L&&(e=this._computePipelineCache),t instanceof r.r&&(e=this._renderPipelineCache),!e)throw Error(`${this}`);if(!e[t.hash])throw Error(`${this}: ${t} matched incorrect entry`);return e}_hashComputePipeline(t){let{type:e}=this.device,i=this._getHash(t.shader.source);return`${e}/C/${i}`}_hashRenderPipeline(t){let e=t.vs?this._getHash(t.vs.source):0,i=t.fs?this._getHash(t.fs.source):0,r=this._getHash(JSON.stringify(t.bufferLayout)),{type:s}=this.device;if("webgl"===s)return`${s}/R/${e}/${i}V-BL${r}`;{let n=this._getHash(JSON.stringify(t.parameters));return`${s}/R/${e}/${i}V-T${t.topology}P${n}BL${r}`}}_getHash(t){return void 0===this._hashes[t]&&(this._hashes[t]=this._hashCounter++),this._hashes[t]}}var x=i(90304);class T{static defaultProps={...x.M.defaultProps};static getDefaultShaderFactory(t){return t._lumaData.defaultShaderFactory||=new T(t),t._lumaData.defaultShaderFactory}device;cachingEnabled;destroyPolicy;debug;_cache={};get[Symbol.toStringTag](){return"ShaderFactory"}toString(){return`${this[Symbol.toStringTag]}(${this.device.id})`}constructor(t){this.device=t,this.cachingEnabled=t.props._cacheShaders,this.destroyPolicy=t.props._cacheDestroyPolicy,this.debug=!0}createShader(t){if(!this.cachingEnabled)return this.device.createShader(t);let e=this._hashShader(t),i=this._cache[e];if(i)i.useCount++,this.debug&&s.R.log(3,`${this}: Reusing shader ${i.shader.id} count=${i.useCount}`)();else{let r=this.device.createShader({...t,id:t.id?`${t.id}-cached`:void 0});this._cache[e]=i={shader:r,useCount:1},this.debug&&s.R.log(3,`${this}: Created new shader ${r.id}`)()}return i.shader}release(t){if(!this.cachingEnabled){t.destroy();return}let e=this._hashShader(t),i=this._cache[e];if(i){if(i.useCount--,0===i.useCount)"unused"===this.destroyPolicy&&(delete this._cache[e],i.shader.destroy(),this.debug&&s.R.log(3,`${this}: Releasing shader ${t.id}, destroyed`)());else if(i.useCount<0)throw Error(`ShaderFactory: Shader ${t.id} released too many times`);else this.debug&&s.R.log(3,`${this}: Releasing shader ${t.id} count=${i.useCount}`)()}}_hashShader(t){return`${t.stage}:${t.source}`}}let E=null,O=null;class S{bufferLayouts;constructor(t){this.bufferLayouts=t}getBufferLayout(t){return this.bufferLayouts.find(e=>e.name===t)||null}getAttributeNamesForBuffer(t){return t.attributes?t.attributes?.map(t=>t.attribute):[t.name]}mergeBufferLayouts(t,e){let i=[...t];for(let t of e){let e=i.findIndex(e=>e.name===t.name);e<0?i.push(t):i[e]=t}return i}getBufferIndex(t){let e=this.bufferLayouts.findIndex(e=>e.name===t);return -1===e&&s.R.warn(`BufferLayout: Missing buffer for "${t}".`)(),e}}var R=i(45480);class I{options={disableWarnings:!1};modules;moduleUniforms;moduleBindings;constructor(t,e){for(let i of(Object.assign(this.options,e),(0,R.$Q)(Object.values(t).filter(t=>t.dependencies))))t[i.name]=i;for(let[e,i]of(s.R.log(1,"Creating ShaderInputs with modules",Object.keys(t))(),this.modules=t,this.moduleUniforms={},this.moduleBindings={},Object.entries(t)))this._addModule(i),i.name&&e!==i.name&&!this.options.disableWarnings&&s.R.warn(`Module name: ${e} vs ${i.name}`)()}destroy(){}setProps(t){for(let e of Object.keys(t)){let i=t[e]||{},r=this.modules[e];if(!r){this.options.disableWarnings||s.R.warn(`Module ${e} not found`)();continue}let n=this.moduleUniforms[e],o=this.moduleBindings[e],{uniforms:a,bindings:l}=function(t){let e={bindings:{},uniforms:{}};return Object.keys(t).forEach(i=>{let r=t[i];(!ArrayBuffer.isView(r)||r instanceof DataView)&&(Array.isArray(r)?0!==r.length&&"number"!=typeof r[0]:1)&&"number"!=typeof r&&"boolean"!=typeof r?e.bindings[i]=r:e.uniforms[i]=r}),e}(r.getUniforms?.(i,n)||i);this.moduleUniforms[e]={...n,...a},this.moduleBindings[e]={...o,...l}}}getModules(){return Object.values(this.modules)}getUniformValues(){return this.moduleUniforms}getBindingValues(){let t={};for(let e of Object.values(this.moduleBindings))Object.assign(t,e);return t}getDebugTable(){let t={};for(let[e,i]of Object.entries(this.moduleUniforms))for(let[r,s]of Object.entries(i))t[`${e}.${r}`]={type:this.modules[e].uniformTypes?.[r],value:String(s)};return t}_addModule(t){let e=t.name;this.moduleUniforms[e]=t.defaultUniforms||{},this.moduleBindings[e]={}}}async function B(t,e){let i=new Image;return i.crossOrigin=e?.crossOrigin||"anonymous",i.src=t.startsWith("http")?t:""+t,await i.decode(),e?await createImageBitmap(i,e):await createImageBitmap(i)}let N=["+X","-X","+Y","-Y","+Z","-Z"],U=["+X","-X","+Y","-Y","+Z","-Z"];class D{device;id;props;texture;sampler;view;ready;isReady=!1;destroyed=!1;resolveReady=()=>{};rejectReady=()=>{};get[Symbol.toStringTag](){return"AsyncTexture"}toString(){return`AsyncTexture:"${this.id}"(${this.isReady?"ready":"loading"})`}constructor(t,e){this.device=t;let i=(0,A.L)("async-texture");this.props={...D.defaultProps,id:i,...e},this.id=this.props.id,e={...e},"string"==typeof e?.data&&"2d"===e.dimension&&(e.data=B(e.data)),e.mipmaps&&(e.mipLevels="auto"),this.ready=new Promise((t,e)=>{this.resolveReady=()=>{this.isReady=!0,t()},this.rejectReady=e}),this.initAsync(e)}async initAsync(t){let e=t.data,i=await F(e).then(void 0,this.rejectReady);if(this.destroyed)return;let r=this.props.width&&this.props.height?{width:this.props.width,height:this.props.height}:this.getTextureDataSize(i);if(!r)throw Error("Texture size could not be determined");let n={...r,...t,data:void 0,mipLevels:1},o=this.device.getMipLevelCount(n.width,n.height);if(n.mipLevels="auto"===this.props.mipLevels?o:Math.min(o,this.props.mipLevels),this.texture=this.device.createTexture(n),this.sampler=this.texture.sampler,this.view=this.texture.view,t.data)switch(this.props.dimension){case"1d":this._setTexture1DData(this.texture,i);break;case"2d":this._setTexture2DData(i);break;case"3d":this._setTexture3DData(this.texture,i);break;case"2d-array":this._setTextureArrayData(this.texture,i);break;case"cube":this._setTextureCubeData(this.texture,i);break;case"cube-array":this._setTextureCubeArrayData(this.texture,i)}this.props.mipmaps&&this.generateMipmaps(),s.R.info(1,`${this} loaded`),this.resolveReady()}destroy(){this.texture&&(this.texture.destroy(),this.texture=null),this.destroyed=!0}generateMipmaps(){this.texture.generateMipmapsWebGL()}setSampler(t={}){this.texture.setSampler(t instanceof g.L?t:this.device.createSampler(t))}resize(t){if(!this.isReady)throw Error("Cannot resize texture before it is ready");if(t.width===this.texture.width&&t.height===this.texture.height)return!1;if(this.texture){let e=this.texture;this.texture=e.clone(t),e.destroy()}return!0}isTextureLevelData(t){return ArrayBuffer.isView(t?.data)}getTextureDataSize(t){if(!t||ArrayBuffer.isView(t))return null;if(Array.isArray(t))return this.getTextureDataSize(t[0]);if(this.device.isExternalImage(t))return this.device.getExternalImageSize(t);if(t&&"object"==typeof t&&t.constructor===Object){let e=Object.values(t)[0];return{width:e.width,height:e.height}}throw Error("texture size deduction failed")}getCubeFaceDepth(t){switch(t){case"+X":return 0;case"-X":return 1;case"+Y":return 2;case"-Y":return 3;case"+Z":return 4;case"-Z":return 5;default:throw Error(t)}}setTextureData(t){}_setTexture1DData(t,e){throw Error("setTexture1DData not supported in WebGL.")}_setTexture2DData(t,e=0){if(!this.texture)throw Error("Texture not initialized");let i=this._normalizeTextureData(t);i.length>1&&!1!==this.props.mipmaps&&s.R.warn(`Texture ${this.id} mipmap and multiple LODs.`)();for(let t=0;t<i.length;t++){let r=i[t];this.device.isExternalImage(r)?this.texture.copyExternalImage({image:r,depth:e,mipLevel:t,flipY:!0}):this.texture.copyImageData({data:r.data,mipLevel:t})}}_setTexture3DData(t,e){if(this.texture?.props.dimension!=="3d")throw Error(this.id);for(let t=0;t<e.length;t++)this._setTexture2DData(e[t],t)}_setTextureCubeData(t,e){if(this.texture?.props.dimension!=="cube")throw Error(this.id);for(let[t,i]of Object.entries(e)){let e=U.indexOf(t);this._setTexture2DData(i,e)}}_setTextureArrayData(t,e){if(this.texture?.props.dimension!=="2d-array")throw Error(this.id);for(let t=0;t<e.length;t++)this._setTexture2DData(e[t],t)}_setTextureCubeArrayData(t,e){throw Error("setTextureCubeArrayData not supported in WebGL2.")}_setTextureCubeFaceData(t,e,i,r=0){Array.isArray(e)&&e.length>1&&!1!==this.props.mipmaps&&s.R.warn(`${this.id} has mipmap and multiple LODs.`)();let n=N.indexOf(i);this._setTexture2DData(e,n)}_normalizeTextureData(t){let e=this.texture;return ArrayBuffer.isView(t)?[{data:t,width:e.width,height:e.height}]:Array.isArray(t)?t:[t]}static defaultProps={...p.g.defaultProps,data:null,mipmaps:!1}}async function F(t){if(Array.isArray(t=await t))return await Promise.all(t.map(F));if(t&&"object"==typeof t&&t.constructor===Object){let e=t,i=await Promise.all(Object.values(e)),r=Object.keys(e),s={};for(let t=0;t<r.length;t++)s[r[t]]=i[t];return s}return t}class k{static defaultProps={...r.r.defaultProps,source:void 0,vs:null,fs:null,id:"unnamed",handle:void 0,userData:{},defines:{},modules:[],geometry:null,indexBuffer:null,attributes:{},constantAttributes:{},varyings:[],isInstanced:void 0,instanceCount:0,vertexCount:0,shaderInputs:void 0,pipelineFactory:void 0,shaderFactory:void 0,transformFeedback:void 0,shaderAssembler:b._.getDefaultShaderAssembler(),debugShaders:void 0,disableWarnings:void 0};device;id;source;vs;fs;pipelineFactory;shaderFactory;userData={};parameters;topology;bufferLayout;isInstanced=void 0;instanceCount=0;vertexCount;indexBuffer=null;bufferAttributes={};constantAttributes={};bindings={};vertexArray;transformFeedback=null;pipeline;shaderInputs;_uniformStore;_attributeInfos={};_gpuGeometry=null;props;_pipelineNeedsUpdate="newly created";_needsRedraw="initializing";_destroyed=!1;_lastDrawTimestamp=-1;get[Symbol.toStringTag](){return"Model"}toString(){return`Model(${this.id})`}constructor(t,e){this.props={...k.defaultProps,...e},e=this.props,this.id=e.id||(0,A.L)("model"),this.device=t,Object.assign(this.userData,e.userData);let i=Object.fromEntries(this.props.modules?.map(t=>[t.name,t])||[]),r=e.shaderInputs||new I(i,{disableWarnings:this.props.disableWarnings});this.setShaderInputs(r);let n=function(t){return{type:t.type,shaderLanguage:t.info.shadingLanguage,shaderLanguageVersion:t.info.shadingLanguageVersion,gpu:t.info.gpu,features:t.features}}(t),o=(this.props.modules?.length>0?this.props.modules:this.shaderInputs?.getModules())||[];if("webgpu"===this.device.type&&this.props.source){let{source:t,getUniforms:e}=this.props.shaderAssembler.assembleWGSLShader({platformInfo:n,...this.props,modules:o});this.source=t,this._getModuleUniforms=e,this.props.shaderLayout||=function(t){let e;let i={attributes:[],bindings:[]};try{e=function(t){try{return new y.$X(t)}catch(e){if(e instanceof Error)throw e;let t="WGSL parse error";throw"object"==typeof e&&e?.message&&(t+=`: ${e.message} `),"object"==typeof e&&e?.token&&(t+=e.token.line||""),Error(t,{cause:e})}}(t)}catch(t){return s.R.error(t.message)(),i}for(let t of e.uniforms){let e=[];for(let i of t.type?.members||[])e.push({name:i.name,type:v(i.type)});i.bindings.push({type:"uniform",name:t.name,group:t.group,location:t.binding,members:e})}for(let t of e.textures)i.bindings.push({type:"texture",name:t.name,group:t.group,location:t.binding});for(let t of e.samplers)i.bindings.push({type:"sampler",name:t.name,group:t.group,location:t.binding});let r=e.entry.vertex[0],n=r?.inputs.length||0;for(let t=0;t<n;t++){let e=r.inputs[t];if("location"===e.locationType){let t=v(e.type);i.attributes.push({name:e.name,location:Number(e.location),type:t})}}return i}(this.source)}else{let{vs:t,fs:e,getUniforms:i}=this.props.shaderAssembler.assembleGLSLShaderPair({platformInfo:n,...this.props,modules:o});this.vs=t,this.fs=e,this._getModuleUniforms=i}this.vertexCount=this.props.vertexCount,this.instanceCount=this.props.instanceCount,this.topology=this.props.topology,this.bufferLayout=this.props.bufferLayout,this.parameters=this.props.parameters,e.geometry&&this.setGeometry(e.geometry),this.pipelineFactory=e.pipelineFactory||P.getDefaultPipelineFactory(this.device),this.shaderFactory=e.shaderFactory||T.getDefaultShaderFactory(this.device),this.pipeline=this._updatePipeline(),this.vertexArray=t.createVertexArray({shaderLayout:this.pipeline.shaderLayout,bufferLayout:this.pipeline.bufferLayout}),this._gpuGeometry&&this._setGeometryAttributes(this._gpuGeometry),"isInstanced"in e&&(this.isInstanced=e.isInstanced),e.instanceCount&&this.setInstanceCount(e.instanceCount),e.vertexCount&&this.setVertexCount(e.vertexCount),e.indexBuffer&&this.setIndexBuffer(e.indexBuffer),e.attributes&&this.setAttributes(e.attributes),e.constantAttributes&&this.setConstantAttributes(e.constantAttributes),e.bindings&&this.setBindings(e.bindings),e.transformFeedback&&(this.transformFeedback=e.transformFeedback),Object.seal(this)}destroy(){this._destroyed||(this.pipelineFactory.release(this.pipeline),this.shaderFactory.release(this.pipeline.vs),this.pipeline.fs&&this.shaderFactory.release(this.pipeline.fs),this._uniformStore.destroy(),this._gpuGeometry?.destroy(),this._destroyed=!0)}needsRedraw(){this._getBindingsUpdateTimestamp()>this._lastDrawTimestamp&&this.setNeedsRedraw("contents of bound textures or buffers updated");let t=this._needsRedraw;return this._needsRedraw=!1,t}setNeedsRedraw(t){this._needsRedraw||=t}predraw(){this.updateShaderInputs(),this.pipeline=this._updatePipeline()}draw(t){let e;let i=this._areBindingsLoading();if(i)return s.R.info(2,`>>> DRAWING ABORTED ${this.id}: ${i} not loaded`)(),!1;try{t.pushDebugGroup(`${this}.predraw(${t})`),this.predraw()}finally{t.popDebugGroup()}try{t.pushDebugGroup(`${this}.draw(${t})`),this._logDrawCallStart(),this.pipeline=this._updatePipeline();let i=this._getBindings();this.pipeline.setBindings(i,{disableWarnings:this.props.disableWarnings});let{indexBuffer:r}=this.vertexArray,s=r?r.byteLength/("uint32"===r.indexType?4:2):void 0;e=this.pipeline.draw({renderPass:t,vertexArray:this.vertexArray,isInstanced:this.isInstanced,vertexCount:this.vertexCount,instanceCount:this.instanceCount,indexCount:s,transformFeedback:this.transformFeedback||void 0,parameters:this.parameters,topology:this.topology})}finally{t.popDebugGroup(),this._logDrawCallEnd()}return this._logFramebuffer(t),e?(this._lastDrawTimestamp=this.device.timestamp,this._needsRedraw=!1):this._needsRedraw="waiting for resource initialization",e}setGeometry(t){this._gpuGeometry?.destroy();let e=t&&function(t,e){if(e instanceof w)return e;let i=function(t,e){if(!e.indices)return;let i=e.indices.value;return t.createBuffer({usage:n.h.INDEX,data:i})}(t,e),{attributes:r,bufferLayout:s}=function(t,e){let i=[],r={};for(let[s,n]of Object.entries(e.attributes)){let e=s;switch(s){case"POSITION":e="positions";break;case"NORMAL":e="normals";break;case"TEXCOORD_0":e="texCoords";break;case"COLOR_0":e="colors"}if(n){r[e]=t.createBuffer({data:n.value,id:`${s}-buffer`});let{value:o,size:a,normalized:l}=n;i.push({name:e,format:(0,_.OB)(o,a,l)})}}return{attributes:r,bufferLayout:i,vertexCount:e._calculateVertexCount(e.attributes,e.indices)}}(t,e);return new w({topology:e.topology||"triangle-list",bufferLayout:s,vertexCount:e.vertexCount,indices:i,attributes:r})}(this.device,t);if(e){this.setTopology(e.topology||"triangle-list");let t=new S(this.bufferLayout);this.bufferLayout=t.mergeBufferLayouts(e.bufferLayout,this.bufferLayout),this.vertexArray&&this._setGeometryAttributes(e)}this._gpuGeometry=e}setTopology(t){t!==this.topology&&(this.topology=t,this._setPipelineNeedsUpdate("topology"))}setBufferLayout(t){let e=new S(this.bufferLayout);this.bufferLayout=this._gpuGeometry?e.mergeBufferLayouts(t,this._gpuGeometry.bufferLayout):t,this._setPipelineNeedsUpdate("bufferLayout"),this.pipeline=this._updatePipeline(),this.vertexArray=this.device.createVertexArray({shaderLayout:this.pipeline.shaderLayout,bufferLayout:this.pipeline.bufferLayout}),this._gpuGeometry&&this._setGeometryAttributes(this._gpuGeometry)}setParameters(t){!function t(e,i,r){if(e===i)return!0;if(!r||!e||!i)return!1;if(Array.isArray(e)){if(!Array.isArray(i)||e.length!==i.length)return!1;for(let s=0;s<e.length;s++)if(!t(e[s],i[s],r-1))return!1;return!0}if(Array.isArray(i))return!1;if("object"==typeof e&&"object"==typeof i){let s=Object.keys(e),n=Object.keys(i);if(s.length!==n.length)return!1;for(let n of s)if(!i.hasOwnProperty(n)||!t(e[n],i[n],r-1))return!1;return!0}return!1}(t,this.parameters,2)&&(this.parameters=t,this._setPipelineNeedsUpdate("parameters"))}setInstanceCount(t){this.instanceCount=t,void 0===this.isInstanced&&t>0&&(this.isInstanced=!0),this.setNeedsRedraw("instanceCount")}setVertexCount(t){this.vertexCount=t,this.setNeedsRedraw("vertexCount")}setShaderInputs(t){for(let[e,i]of(this.shaderInputs=t,this._uniformStore=new c(this.shaderInputs.modules),Object.entries(this.shaderInputs.modules)))if(i.uniformTypes&&!function(t){for(let e in t)return!1;return!0}(i.uniformTypes)){let t=this._uniformStore.getManagedUniformBuffer(this.device,e);this.bindings[`${e}Uniforms`]=t}this.setNeedsRedraw("shaderInputs")}updateShaderInputs(){this._uniformStore.setUniforms(this.shaderInputs.getUniformValues()),this.setBindings(this.shaderInputs.getBindingValues()),this.setNeedsRedraw("shaderInputs")}setBindings(t){Object.assign(this.bindings,t),this.setNeedsRedraw("bindings")}setTransformFeedback(t){this.transformFeedback=t,this.setNeedsRedraw("transformFeedback")}setIndexBuffer(t){this.vertexArray.setIndexBuffer(t),this.setNeedsRedraw("indexBuffer")}setAttributes(t,e){let i=e?.disableWarnings??this.props.disableWarnings;t.indices&&s.R.warn(`Model:${this.id} setAttributes() - indexBuffer should be set using setIndexBuffer()`)(),this.bufferLayout=function(t,e){let i=Object.fromEntries(t.attributes.map(t=>[t.name,t.location])),r=e.slice();return r.sort((t,e)=>{let r=t.attributes?t.attributes.map(t=>t.attribute):[t.name],s=e.attributes?e.attributes.map(t=>t.attribute):[e.name];return Math.min(...r.map(t=>i[t]))-Math.min(...s.map(t=>i[t]))}),r}(this.pipeline.shaderLayout,this.bufferLayout);let r=new S(this.bufferLayout);for(let[e,n]of Object.entries(t)){let t=r.getBufferLayout(e);if(!t){i||s.R.warn(`Model(${this.id}): Missing layout for buffer "${e}".`)();continue}let o=r.getAttributeNamesForBuffer(t),a=!1;for(let t of o){let e=this._attributeInfos[t];if(e){let t="webgpu"===this.device.type?r.getBufferIndex(e.bufferName):e.location;this.vertexArray.setBuffer(t,n),a=!0}}a||i||s.R.warn(`Model(${this.id}): Ignoring buffer "${n.id}" for unknown attribute "${e}"`)()}this.setNeedsRedraw("attributes")}setConstantAttributes(t,e){for(let[i,r]of Object.entries(t)){let t=this._attributeInfos[i];t?this.vertexArray.setConstantWebGL(t.location,r):(e?.disableWarnings??this.props.disableWarnings)||s.R.warn(`Model "${this.id}: Ignoring constant supplied for unknown attribute "${i}"`)()}this.setNeedsRedraw("constants")}_areBindingsLoading(){for(let t of Object.values(this.bindings))if(t instanceof D&&!t.isReady)return t.id;return!1}_getBindings(){let t={};for(let[e,i]of Object.entries(this.bindings))i instanceof D?i.isReady&&(t[e]=i.texture):t[e]=i;return t}_getBindingsUpdateTimestamp(){let t=0;for(let e of Object.values(this.bindings))e instanceof f.X?t=Math.max(t,e.texture.updateTimestamp):e instanceof n.h||e instanceof p.g?t=Math.max(t,e.updateTimestamp):e instanceof D?t=e.texture?Math.max(t,e.texture.updateTimestamp):1/0:e instanceof g.L||(t=Math.max(t,e.buffer.updateTimestamp));return t}_setGeometryAttributes(t){let e={...t.attributes};for(let[t]of Object.entries(e))this.pipeline.shaderLayout.attributes.find(e=>e.name===t)||"positions"===t||delete e[t];this.vertexCount=t.vertexCount,this.setIndexBuffer(t.indices||null),this.setAttributes(t.attributes,{disableWarnings:!0}),this.setAttributes(e,{disableWarnings:this.props.disableWarnings}),this.setNeedsRedraw("geometry attributes")}_setPipelineNeedsUpdate(t){this._pipelineNeedsUpdate||=t,this.setNeedsRedraw(t)}_updatePipeline(){if(this._pipelineNeedsUpdate){let t=null,e=null;this.pipeline&&(s.R.log(1,`Model ${this.id}: Recreating pipeline because "${this._pipelineNeedsUpdate}".`)(),t=this.pipeline.vs,e=this.pipeline.fs),this._pipelineNeedsUpdate=!1;let i=this.shaderFactory.createShader({id:`${this.id}-vertex`,stage:"vertex",source:this.source||this.vs,debugShaders:this.props.debugShaders}),r=null;this.source?r=i:this.fs&&(r=this.shaderFactory.createShader({id:`${this.id}-fragment`,stage:"fragment",source:this.source||this.fs,debugShaders:this.props.debugShaders})),this.pipeline=this.pipelineFactory.createRenderPipeline({...this.props,bufferLayout:this.bufferLayout,topology:this.topology,parameters:this.parameters,bindings:this._getBindings(),vs:i,fs:r}),this._attributeInfos=(0,m.P)(this.pipeline.shaderLayout,this.bufferLayout),t&&this.shaderFactory.release(t),e&&this.shaderFactory.release(e)}return this.pipeline}_lastLogTime=0;_logOpen=!1;_logDrawCallStart(){let t=s.R.level>3?0:1e4;s.R.level<2||Date.now()-this._lastLogTime<t||(this._lastLogTime=Date.now(),this._logOpen=!0,s.R.group(2,`>>> DRAWING MODEL ${this.id}`,{collapsed:s.R.level<=2})())}_logDrawCallEnd(){if(this._logOpen){let t=function(t,e){let i={},r="Values";if(0===t.attributes.length&&!t.varyings?.length)return{"No attributes or varyings":{[r]:"N/A"}};for(let e of t.attributes)if(e){let t=`${e.location} ${e.name}: ${e.type}`;i[`in ${t}`]={[r]:e.stepMode||"vertex"}}for(let e of t.varyings||[]){let t=`${e.location} ${e.name}`;i[`out ${t}`]={[r]:JSON.stringify(e)}}return i}(this.pipeline.shaderLayout,this.id);s.R.table(2,t)();let e=this.shaderInputs.getDebugTable();s.R.table(2,e)();let i=this._getAttributeDebugTable();s.R.table(2,this._attributeInfos)(),s.R.table(2,i)(),s.R.groupEnd(2)(),this._logOpen=!1}}_drawCount=0;_logFramebuffer(t){let e=this.device.props.debugFramebuffers;if(this._drawCount++,!e)return;let i=t.props.framebuffer;i&&function(t,{id:e,minimap:i,opaque:r,top:s="0",left:n="0",rgbaScale:o=1}){E||((E=document.createElement("canvas")).id=e,E.title=e,E.style.zIndex="100",E.style.position="absolute",E.style.top=s,E.style.left=n,E.style.border="blue 5px solid",E.style.transform="scaleY(-1)",document.body.appendChild(E),O=E.getContext("2d")),(E.width!==t.width||E.height!==t.height)&&(E.width=t.width/2,E.height=t.height/2,E.style.width="400px",E.style.height="400px");let a=t.device.readPixelsToArrayWebGL(t),l=O?.createImageData(t.width,t.height);if(l){for(let t=0;t<a.length;t+=4)l.data[0+t+0]=a[t+0]*o,l.data[0+t+1]=a[t+1]*o,l.data[0+t+2]=a[t+2]*o,l.data[0+t+3]=r?255:a[t+3]*o;O?.putImageData(l,0,0)}}(i,{id:i.id,minimap:!0})}_getAttributeDebugTable(){let t={};for(let[e,i]of Object.entries(this._attributeInfos)){let r=this.vertexArray.attributes[i.location];t[i.location]={name:e,type:i.shaderType,values:r?this._getBufferOrConstantValues(r,i.bufferDataType):"null"}}if(this.vertexArray.indexBuffer){let{indexBuffer:e}=this.vertexArray,i="uint32"===e.indexType?new Uint32Array(e.debugData):new Uint16Array(e.debugData);t.indices={name:"indices",type:e.indexType,values:i.toString()}}return t}_getBufferOrConstantValues(t,e){let i=(0,l.Ak)(e);return(t instanceof n.h?new i(t.debugData):t).toString()}}},83349:(t,e,i)=>{i.d(e,{L:()=>s});let r={};function s(t="id"){r[t]=r[t]||1;let e=r[t]++;return`${t}-${e}`}},75817:(t,e,i)=>{i.d(e,{J:()=>o});var r=i(80140),s=i(29879),n=i(79350);let o={props:{},name:"gouraudMaterial",vs:s.l.replace("phongMaterial","gouraudMaterial"),fs:s.X.replace("phongMaterial","gouraudMaterial"),source:n.X.replaceAll("phongMaterial","gouraudMaterial"),defines:{LIGHTING_VERTEX:!0},dependencies:[r.x],uniformTypes:{ambient:"f32",diffuse:"f32",shininess:"f32",specularColor:"vec3<f32>"},defaultUniforms:{ambient:.35,diffuse:.6,shininess:32,specularColor:[.15,.15,.15]},getUniforms(t){let e={...t};return e.specularColor&&(e.specularColor=e.specularColor.map(t=>t/255)),{...o.defaultUniforms,...e}}}},80140:(t,e,i)=>{i.d(e,{x:()=>a});var r,s=i(64578);let n=`\
precision highp int;

// #if (defined(SHADER_TYPE_FRAGMENT) && defined(LIGHTING_FRAGMENT)) || (defined(SHADER_TYPE_VERTEX) && defined(LIGHTING_VERTEX))
struct AmbientLight {
  vec3 color;
};

struct PointLight {
  vec3 color;
  vec3 position;
  vec3 attenuation; // 2nd order x:Constant-y:Linear-z:Exponential
};

struct DirectionalLight {
  vec3 color;
  vec3 direction;
};

uniform lightingUniforms {
  int enabled;
  int lightType;

  int directionalLightCount;
  int pointLightCount;

  vec3 ambientColor;

  vec3 lightColor0;
  vec3 lightPosition0;
  vec3 lightDirection0;
  vec3 lightAttenuation0;

  vec3 lightColor1;
  vec3 lightPosition1;
  vec3 lightDirection1;
  vec3 lightAttenuation1;

  vec3 lightColor2;
  vec3 lightPosition2;
  vec3 lightDirection2;
  vec3 lightAttenuation2;
} lighting;

PointLight lighting_getPointLight(int index) {
  switch (index) {
    case 0:
      return PointLight(lighting.lightColor0, lighting.lightPosition0, lighting.lightAttenuation0);
    case 1:
      return PointLight(lighting.lightColor1, lighting.lightPosition1, lighting.lightAttenuation1);
    case 2:
    default:  
      return PointLight(lighting.lightColor2, lighting.lightPosition2, lighting.lightAttenuation2);
  }
}

DirectionalLight lighting_getDirectionalLight(int index) {
  switch (index) {
    case 0:
      return DirectionalLight(lighting.lightColor0, lighting.lightDirection0);
    case 1:
      return DirectionalLight(lighting.lightColor1, lighting.lightDirection1);
    case 2:
    default:   
      return DirectionalLight(lighting.lightColor2, lighting.lightDirection2);
  }
} 

float getPointLightAttenuation(PointLight pointLight, float distance) {
  return pointLight.attenuation.x
       + pointLight.attenuation.y * distance
       + pointLight.attenuation.z * distance * distance;
}

// #endif
`,o=`\
// #if (defined(SHADER_TYPE_FRAGMENT) && defined(LIGHTING_FRAGMENT)) || (defined(SHADER_TYPE_VERTEX) && defined(LIGHTING_VERTEX))
struct AmbientLight {
  color: vec3<f32>,
};

struct PointLight {
  color: vec3<f32>,
  position: vec3<f32>,
  attenuation: vec3<f32>, // 2nd order x:Constant-y:Linear-z:Exponential
};

struct DirectionalLight {
  color: vec3<f32>,
  direction: vec3<f32>,
};

struct lightingUniforms {
  enabled: i32,
  pointLightCount: i32,
  directionalLightCount: i32,

  ambientColor: vec3<f32>,

  // TODO - support multiple lights by uncommenting arrays below
  lightType: i32,
  lightColor: vec3<f32>,
  lightDirection: vec3<f32>,
  lightPosition: vec3<f32>,
  lightAttenuation: vec3<f32>,

  // AmbientLight ambientLight;
  // PointLight pointLight[MAX_LIGHTS];
  // DirectionalLight directionalLight[MAX_LIGHTS];
};

// Binding 0:1 is reserved for lighting (Note: could go into separate bind group as it is stable across draw calls)
@binding(1) @group(0) var<uniform> lighting : lightingUniforms;

fn lighting_getPointLight(index: i32) -> PointLight {
  return PointLight(lighting.lightColor, lighting.lightPosition, lighting.lightAttenuation);
}

fn lighting_getDirectionalLight(index: i32) -> DirectionalLight {
  return DirectionalLight(lighting.lightColor, lighting.lightDirection);
} 

fn getPointLightAttenuation(pointLight: PointLight, distance: f32) -> f32 {
  return pointLight.attenuation.x
       + pointLight.attenuation.y * distance
       + pointLight.attenuation.z * distance * distance;
}
`;!function(t){t[t.POINT=0]="POINT",t[t.DIRECTIONAL=1]="DIRECTIONAL"}(r||(r={}));let a={props:{},uniforms:{},name:"lighting",defines:{},uniformTypes:{enabled:"i32",lightType:"i32",directionalLightCount:"i32",pointLightCount:"i32",ambientColor:"vec3<f32>",lightColor0:"vec3<f32>",lightPosition0:"vec3<f32>",lightDirection0:"vec3<f32>",lightAttenuation0:"vec3<f32>",lightColor1:"vec3<f32>",lightPosition1:"vec3<f32>",lightDirection1:"vec3<f32>",lightAttenuation1:"vec3<f32>",lightColor2:"vec3<f32>",lightPosition2:"vec3<f32>",lightDirection2:"vec3<f32>",lightAttenuation2:"vec3<f32>"},defaultUniforms:{enabled:1,lightType:r.POINT,directionalLightCount:0,pointLightCount:0,ambientColor:[.1,.1,.1],lightColor0:[1,1,1],lightPosition0:[1,1,2],lightDirection0:[1,1,1],lightAttenuation0:[1,0,0],lightColor1:[1,1,1],lightPosition1:[1,1,2],lightDirection1:[1,1,1],lightAttenuation1:[1,0,0],lightColor2:[1,1,1],lightPosition2:[1,1,2],lightDirection2:[1,1,1],lightAttenuation2:[1,0,0]},source:o,vs:n,fs:n,getUniforms:function(t,e={}){if(!(t=t?{...t}:t))return{...a.defaultUniforms};t.lights&&(t={...t,...function(t){let e={pointLights:[],directionalLights:[]};for(let i of t||[])switch(i.type){case"ambient":e.ambientLight=i;break;case"directional":e.directionalLights?.push(i);break;case"point":e.pointLights?.push(i)}return e}(t.lights),lights:void 0});let{ambientLight:i,pointLights:n,directionalLights:o}=t||{};if(!(i||n&&n.length>0||o&&o.length>0))return{...a.defaultUniforms,enabled:0};let u={...a.defaultUniforms,...e,...function({ambientLight:t,pointLights:e=[],directionalLights:i=[]}){let n={};n.ambientColor=l(t);let o=0;for(let t of e){n.lightType=r.POINT;let e=o;n[`lightColor${e}`]=l(t),n[`lightPosition${e}`]=t.position,n[`lightAttenuation${e}`]=t.attenuation||[1,0,0],o++}for(let t of i){n.lightType=r.DIRECTIONAL;let e=o;n[`lightColor${e}`]=l(t),n[`lightDirection${e}`]=t.direction,o++}return o>5&&s.R.warn("MAX_LIGHTS exceeded")(),n.directionalLightCount=i.length,n.pointLightCount=e.length,n}({ambientLight:i,pointLights:n,directionalLights:o})};return void 0!==t.enabled&&(u.enabled=t.enabled?1:0),u}};function l(t={}){let{color:e=[0,0,0],intensity:i=1}=t;return e.map(t=>t*i/255)}},4387:(t,e,i)=>{i.d(e,{w:()=>o});var r=i(80140),s=i(79350),n=i(29879);let o={name:"phongMaterial",dependencies:[r.x],source:s.X,vs:n.X,fs:n.l,defines:{LIGHTING_FRAGMENT:!0},uniformTypes:{ambient:"f32",diffuse:"f32",shininess:"f32",specularColor:"vec3<f32>"},defaultUniforms:{ambient:.35,diffuse:.6,shininess:32,specularColor:[.15,.15,.15]},getUniforms(t){let e={...t};return e.specularColor&&(e.specularColor=e.specularColor.map(t=>t/255)),{...o.defaultUniforms,...e}}}},29879:(t,e,i)=>{i.d(e,{X:()=>r,l:()=>s});let r=`\
uniform phongMaterialUniforms {
  uniform float ambient;
  uniform float diffuse;
  uniform float shininess;
  uniform vec3  specularColor;
} material;
`,s=`\
#define MAX_LIGHTS 3

uniform phongMaterialUniforms {
  uniform float ambient;
  uniform float diffuse;
  uniform float shininess;
  uniform vec3  specularColor;
} material;

vec3 lighting_getLightColor(vec3 surfaceColor, vec3 light_direction, vec3 view_direction, vec3 normal_worldspace, vec3 color) {
  vec3 halfway_direction = normalize(light_direction + view_direction);
  float lambertian = dot(light_direction, normal_worldspace);
  float specular = 0.0;
  if (lambertian > 0.0) {
    float specular_angle = max(dot(normal_worldspace, halfway_direction), 0.0);
    specular = pow(specular_angle, material.shininess);
  }
  lambertian = max(lambertian, 0.0);
  return (lambertian * material.diffuse * surfaceColor + specular * material.specularColor) * color;
}

vec3 lighting_getLightColor(vec3 surfaceColor, vec3 cameraPosition, vec3 position_worldspace, vec3 normal_worldspace) {
  vec3 lightColor = surfaceColor;

  if (lighting.enabled == 0) {
    return lightColor;
  }

  vec3 view_direction = normalize(cameraPosition - position_worldspace);
  lightColor = material.ambient * surfaceColor * lighting.ambientColor;

  for (int i = 0; i < lighting.pointLightCount; i++) {
    PointLight pointLight = lighting_getPointLight(i);
    vec3 light_position_worldspace = pointLight.position;
    vec3 light_direction = normalize(light_position_worldspace - position_worldspace);
    float light_attenuation = getPointLightAttenuation(pointLight, distance(light_position_worldspace, position_worldspace));
    lightColor += lighting_getLightColor(surfaceColor, light_direction, view_direction, normal_worldspace, pointLight.color / light_attenuation);
  }

  int totalLights = min(MAX_LIGHTS, lighting.pointLightCount + lighting.directionalLightCount);
  for (int i = lighting.pointLightCount; i < totalLights; i++) {
    DirectionalLight directionalLight = lighting_getDirectionalLight(i);
    lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
  }
  
  return lightColor;
}
`},79350:(t,e,i)=>{i.d(e,{X:()=>r});let r=`\
struct phongMaterialUniforms {
  ambient: f32,
  diffuse: f32,
  shininess: f32,
  specularColor: vec3<f32>,
};

@binding(2) @group(0) var<uniform> phongMaterial : phongMaterialUniforms;

fn lighting_getLightColor(surfaceColor: vec3<f32>, light_direction: vec3<f32>, view_direction: vec3<f32>, normal_worldspace: vec3<f32>, color: vec3<f32>) -> vec3<f32> {
  let halfway_direction: vec3<f32> = normalize(light_direction + view_direction);
  var lambertian: f32 = dot(light_direction, normal_worldspace);
  var specular: f32 = 0.0;
  if (lambertian > 0.0) {
    let specular_angle = max(dot(normal_worldspace, halfway_direction), 0.0);
    specular = pow(specular_angle, phongMaterial.shininess);
  }
  lambertian = max(lambertian, 0.0);
  return (lambertian * phongMaterial.diffuse * surfaceColor + specular * phongMaterial.specularColor) * color;
}

fn lighting_getLightColor2(surfaceColor: vec3<f32>, cameraPosition: vec3<f32>, position_worldspace: vec3<f32>, normal_worldspace: vec3<f32>) -> vec3<f32> {
  var lightColor: vec3<f32> = surfaceColor;

  if (lighting.enabled == 0) {
    return lightColor;
  }

  let view_direction: vec3<f32> = normalize(cameraPosition - position_worldspace);
  lightColor = phongMaterial.ambient * surfaceColor * lighting.ambientColor;

  if (lighting.lightType == 0) {
    let pointLight: PointLight  = lighting_getPointLight(0);
    let light_position_worldspace: vec3<f32> = pointLight.position;
    let light_direction: vec3<f32> = normalize(light_position_worldspace - position_worldspace);
    lightColor += lighting_getLightColor(surfaceColor, light_direction, view_direction, normal_worldspace, pointLight.color);
  } else if (lighting.lightType == 1) {
    var directionalLight: DirectionalLight = lighting_getDirectionalLight(0);
    lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
  }
  
  return lightColor;
  /*
  for (int i = 0; i < MAX_LIGHTS; i++) {
    if (i >= lighting.pointLightCount) {
      break;
    }
    PointLight pointLight = lighting.pointLight[i];
    vec3 light_position_worldspace = pointLight.position;
    vec3 light_direction = normalize(light_position_worldspace - position_worldspace);
    lightColor += lighting_getLightColor(surfaceColor, light_direction, view_direction, normal_worldspace, pointLight.color);
  }

  for (int i = 0; i < MAX_LIGHTS; i++) {
    if (i >= lighting.directionalLightCount) {
      break;
    }
    DirectionalLight directionalLight = lighting.directionalLight[i];
    lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
  }
  */
}

fn lighting_getSpecularLightColor(cameraPosition: vec3<f32>, position_worldspace: vec3<f32>, normal_worldspace: vec3<f32>) -> vec3<f32>{
  var lightColor = vec3<f32>(0, 0, 0);
  let surfaceColor = vec3<f32>(0, 0, 0);

  if (lighting.enabled == 0) {
    let view_direction = normalize(cameraPosition - position_worldspace);

    switch (lighting.lightType) {
      case 0, default: {
        let pointLight: PointLight = lighting_getPointLight(0);
        let light_position_worldspace: vec3<f32> = pointLight.position;
        let light_direction: vec3<f32> = normalize(light_position_worldspace - position_worldspace);
        lightColor += lighting_getLightColor(surfaceColor, light_direction, view_direction, normal_worldspace, pointLight.color);
      }
      case 1: {
        let directionalLight: DirectionalLight = lighting_getDirectionalLight(0);
        lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
      }
    }
  }
  return lightColor;
}
`}}]);