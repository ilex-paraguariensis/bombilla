import getDag from "./get_dag.ts";

const renderValue = (value: any, depth: number = 1): string => {
  if (typeof value === "string") {
    const re = /{(.*)}/;
    if (re.test(value)) {
      return re.exec(value)![1];
    }
    return `"${value}"`;
  }
  if (typeof value === "number") {
    return value.toString();
  }
  if (typeof value === "boolean") {
    return value ? "True" : "False";
  }
  if (Array.isArray(value)) {
    return `[${value.map(renderValue).join(", ")}]`;
  }
  const tabs = "\t".repeat(depth);
  if (typeof value === "object") {
    if ("reference_key" in value) {
      return `${value.reference_key}.${value.function_call}(\n${tabs}${
        Object.entries(value.params).map(
          ([key, value]) => `${key}=${renderValue(value, depth + 1)}`,
        ).join(",\n" + tabs)
      }\n${"\t".repeat(depth - 1)})`;
    }
    return `{${
      Object.entries(value)
        .map(([key, value]) =>
          `\n${tabs}"${key}": ${renderValue(value, depth + 1)}`
        )
        .join(",\n" + tabs)
    }\n${"\t".repeat(depth - 1)}}`;
  }
  return value;
};
export default (bombilla: Record<string, any>): string => {
  const dag = getDag(bombilla);
  const { nodes, edges }: {
    nodes: Map<string, Record<string, any>>;
    edges: [string, string, string[]];
  } = dag;
  // creates a orderedNodes Map with the ordered nodes
  // nodes are ordered starting from the root node
  // the root node is the node with no incoming edges
  const leaves = Array.from(nodes.values()).filter((node) => {
    return edges.filter((edge) => edge[1] === node.object_key).length === 0;
  });
  const orderedNodes = new Map<string, Record<string, any>>(
    leaves.map((node) => [node.object_key, node]),
  );
  const visitedNodes = new Set();
  const visitNode = (node: Record<string, any>) => {
    if (visitedNodes.has(node.object_key)) {
      return;
    }
    visitedNodes.add(node.object_key);
    orderedNodes.set(node.object_key, node);
    const edgesFrom = edges.filter((edge) => edge[0] === node.object_key);
    const children = edgesFrom.map(([from, to, _]) => nodes.get(to)!);
    children.forEach(visitNode);
  };
  Array.from(leaves.values()).forEach(visitNode);
  console.log(orderedNodes.keys());
  const code = [];
  // console.log(nodes);
  for (const [key, value] of orderedNodes) {
    if (
      (("class_type" in value) || ("class_name" in value)) &&
      ("module" in value)
    ) {
      code.push(
        `from ${value.module} import ${
          value.class_name ? value.class_name : value.class_type
        }`,
      );
    } else if ("module" in value) {
      code.push(`import ${value.module}`);
    }
    if (("class_type" in value) || ("class_name" in value)) {
      const params = value.params || {};
      code.push(
        `${value.object_key} = ${
          value.class_name ? value.class_name : value.class_type
        }(\n\t${
          Object.entries(params).map(([key, value]) =>
            `${key}=${renderValue(value, 2)}`
          ).join(",\n\t")
        }\n)`,
      );
    }
    code.push("", "");
  }
  code.push("returns = {");
  for (const [key, value] of nodes) {
    if ("entry_point" in value) {
      code.push(
        `\t"${key}": [\n\t\t${
          value.cue.map((cue: any) => renderValue(cue, 3)).join(",")
        }\n\t],`,
      );
    }
  }
  code.push("}");
  return code.join("\n");
};
