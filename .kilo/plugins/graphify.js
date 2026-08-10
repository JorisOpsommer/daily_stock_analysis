// graphify Kilo plugin
// Intercepts native Grep/search tools and search-like bash commands.
import { existsSync } from "fs";
import { join } from "path";

const BASH_SEARCH_PATTERN = /\b(grep|rg|find|ag|ack)\b/;
// Kilo native search tool names (case-insensitive)
const SEARCH_TOOLS = new Set(["grep", "search", "find", "ripgrep", "glob"]);

const GRAPHIFY_MSG =
  '[graphify] STOP: Use graphify tools first. Run: graphify query "<question>" OR graphify path "A" "B" OR graphify explain "<concept>". Only fall back to grep if graphify gives no result.';

export const GraphifyPlugin = async ({ directory }) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (!existsSync(join(directory, "graphify-out", "graph.json"))) return;

      const toolName = (input.tool || "").toLowerCase();

      // Intercept Kilo's native Grep/Search tools
      if (SEARCH_TOOLS.has(toolName)) {
        // Prepend a warning field Kilo will echo before running the tool
        output.args = { ...output.args, _graphify_warning: GRAPHIFY_MSG };
        return;
      }

      // Intercept bash commands that contain search utilities
      if (
        toolName === "bash" &&
        BASH_SEARCH_PATTERN.test(output.args.command)
      ) {
        output.args.command =
          `echo "${GRAPHIFY_MSG}" && ` + output.args.command;
      }
    },
  };
};
