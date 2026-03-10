import {
  registerTailscaleCommands
} from "./chunk-THRJVD4L.js";
import {
  registerObserveCommand
} from "./chunk-ME37YNW3.js";
import {
  registerReflectCommand
} from "./chunk-3BTHWPMB.js";
import {
  registerContextCommand
} from "./chunk-DTEHFAL7.js";
import {
  registerEmbedCommand
} from "./chunk-4QYGFWRM.js";
import {
  registerInjectCommand
} from "./chunk-4VRIMU4O.js";

// src/cli/index.ts
function registerCliCommands(program) {
  registerContextCommand(program);
  registerInjectCommand(program);
  registerObserveCommand(program);
  registerReflectCommand(program);
  registerEmbedCommand(program);
  registerTailscaleCommands(program);
  return program;
}

export {
  registerCliCommands
};
