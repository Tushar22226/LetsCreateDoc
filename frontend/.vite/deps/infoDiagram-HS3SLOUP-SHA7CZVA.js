import {
  parse
} from "./chunk-EC2RALUT.js";
import "./chunk-HRDZEYVM.js";
import "./chunk-PWZSU7V5.js";
import "./chunk-3SY5WAN3.js";
import "./chunk-4H2AQQW3.js";
import "./chunk-XN26I5PQ.js";
import "./chunk-SUY7NJ7V.js";
import "./chunk-OXYYG5WS.js";
import "./chunk-WPULPGM2.js";
import "./chunk-N7JOPRWO.js";
import {
  package_default
} from "./chunk-CD6NY6GG.js";
import {
  selectSvgElement
} from "./chunk-CMXTFSYB.js";
import {
  configureSvgSize
} from "./chunk-B2GKGLNL.js";
import {
  __name,
  log
} from "./chunk-OTAGEFMD.js";
import "./chunk-SGZ3JTF4.js";
import "./chunk-ZSPGELVN.js";
import "./chunk-DI52DQAC.js";

// node_modules/mermaid/dist/chunks/mermaid.core/infoDiagram-HS3SLOUP.mjs
var parser = {
  parse: __name(async (input) => {
    const ast = await parse("info", input);
    log.debug(ast);
  }, "parse")
};
var DEFAULT_INFO_DB = {
  version: package_default.version + (true ? "" : "-tiny")
};
var getVersion = __name(() => DEFAULT_INFO_DB.version, "getVersion");
var db = {
  getVersion
};
var draw = __name((text, id, version) => {
  log.debug("rendering info diagram\n" + text);
  const svg = selectSvgElement(id);
  configureSvgSize(svg, 100, 400, true);
  const group = svg.append("g");
  group.append("text").attr("x", 100).attr("y", 40).attr("class", "version").attr("font-size", 32).style("text-anchor", "middle").text(`v${version}`);
}, "draw");
var renderer = { draw };
var diagram = {
  parser,
  db,
  renderer
};
export {
  diagram
};
//# sourceMappingURL=infoDiagram-HS3SLOUP-SHA7CZVA.js.map
