// Explicit shared dashboard state. Read mutable collections through accessors so
export const state = {q:'', status:'all', view:'all', sort:'plate', dir:'asc'};
const markers = new Map();
const moves = new Map();
let trucks = [];
let selectedId = null;
let rafId = null;

export function getTruckList(){ return trucks; }
export function setTrucks(next){ trucks = next; }
export function getSelectedId(){ return selectedId; }
export function setSelectedId(id){ selectedId = id; }
export function getMarkers(){ return markers; }
export function getMoves(){ return moves; }
export function getRafId(){ return rafId; }
export function setRafId(id){ rafId = id; }
