// ----- boiler-plate code for vertex shader variable definition
#version 120
//precision highp float;

attribute vec3 vertex;
attribute vec3 normal;
attribute vec2 texcoord;

uniform mat4 modelviewmatrix[3]; // [0] model movement in real coords, [1] in camera coords, [2] camera at light
uniform vec3 unib[5];
//uniform float ntiles => unib[0][0]
//uniform vec2 umult, vmult => unib[2]
//uniform vec2 u_off, v_off => unib[3]
uniform vec3 unif[20];
//uniform vec3 eye > unif[6]
//uniform vec3 lightpos > unif[8]

varying float dist;
varying float fog_start;
varying float is_3d;

varying vec2 texcoordoutf;
varying vec2 texcoordoutb;

void main(void) {
  texcoordoutf = texcoord * unif[14].xy - unif[16].xy;
  texcoordoutb = texcoord * unif[15].xy - unif[17].xy;
  gl_Position = modelviewmatrix[1] * vec4(vertex,1.0);
  dist = gl_Position.z;
  gl_PointSize = unib[2][2] / dist;
}