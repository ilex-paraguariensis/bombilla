export default (bombilla: any) => {
  const edges: [string, string, string[]][] = [];
  const nodes = new Map<string, Record<string, any>>();
  const re = RegExp("{(.*?)}");
  const getStuff = (
    bomb: any,
    path: string[],
    parent: null | Record<string, any> = null,
  ) => {
    if (isSimpleType(bomb)) {
      if (typeof bomb === "string" && re.test(bomb)) {
        console.assert(parent !== null, "parent is null");
        const key = re.exec(bomb)![1];
        edges.push([key, parent!.object_key, path]);
        const slicedPath = sliceFromLastOccurence(parent!._name, path);
        setAt(parent, slicedPath, `{${key}}`);
      }
    } else if (Array.isArray(bomb)) {
      for (const [index, item] of Object.entries(bomb)) {
        getStuff(item, [...path, index.toString()], parent);
      }
    } else if (typeof bomb === "object") {
      if (isMethodArgs(bomb)) {
        for (const [key, value] of Object.entries(bomb.params)) {
          getStuff(value, [...path, "params", key], parent);
        }
      }
      if (isFunctionCall(bomb)) {
        if (parent === null) {
          parent = {
            _name: path[0],
            object_key: path[0],
            entry_point: true,
            cue: [],
          };
          nodes.set(path[0], parent);
        }
        edges.push([bomb.reference_key, parent!.object_key, path]);
        const slicedPath = sliceFromLastOccurence(parent!._name, path);
        setAt(
          parent,
          slicedPath,
          //`{${bomb.reference_key + "." + bomb.function_call + "()"}}`,
          {
            reference_key: bomb.reference_key,
            function_call: bomb.function_call,
            params: bomb.params,
          },
        );

        for (const [key, value] of Object.entries(bomb.params)) {
          getStuff(value, [...path, "params", key], parent);
        }
      }
      if (isModule(bomb)) {
        bomb["_name"] = path.at(-1)!;
        if (!(path.length >= 2) && path.at(-2)! === "params") {
          bomb["object_key"] = path.at(-2)! + "_" + genRanHex(5);
        }
        if (bomb["object_key"] === undefined) {
          if (bomb.class_name || bomb.class_type) {
            bomb["object_key"] = (bomb.class_name ? bomb.class_name : bomb.class_type).split(/\.?(?=[A-Z])/).join('_').toLowerCase();
          } else {
            bomb["object_key"] = genRanHex(5);
          } 
          bomb["object_key"] += "_" + (path.length > 0 ? path.at(-1)! : genRanHex(8)).toString();
        }
        bomb["_path"] = path;
        nodes.set(bomb["object_key"], bomb);
        if (!(parent === null)) {
          edges.push([bomb["object_key"], parent!.object_key, path]);
          const slicedPath = sliceFromLastOccurence(parent!._name, path);
          setAt(parent, slicedPath, `{${bomb["object_key"]}}`);
        }
        if ("params" in bomb) {
          for (const [key, value] of Object.entries(bomb.params)) {
            getStuff(value, [...path, "params", key], bomb);
          }
        }
        if ("method_args" in bomb) {
          for (const [key, value] of bomb.method_args.entries()) {
            getStuff(value, [...path, "method_args", String(key)], bomb);
          }
        }
      } else {
        if (!(path.at(-1)! === "params")) {
          for (const [key, value] of Object.entries(bomb)) {
            getStuff(value, [...path, key], parent);
          }
        }
      }
    }
  };
  getStuff(bombilla, []);
  return { edges, nodes };
};
const setAt = (obj: any, path: string[], value: any) => {
  const last = path.pop() as string;

  const parent = path.reduce((xs, x) => (xs && xs[x] ? xs[x] : null), obj);
  if (parent) {
    if ("entry_point" in parent) {
      parent.cue.push(value);
    } else {
      parent[last] = value;
    }
  }
};
const sliceFromLastOccurence = (str: string, path: string[]) => {
  const lastOccurence = path.lastIndexOf(str);
  return path.slice(lastOccurence + 1);
};
const isNumeric = (str: string) => {
  if (typeof str != "string") return false; // we only process strings!
  return (
    !isNaN(str as unknown as number) && // use type coercion to parse the _entirety_ of the string (`parseFloat` alone does not do this)...
    !isNaN(parseFloat(str))
  ); // ...and ensure strings of whitespace fail
};
const isFunctionCall = (obj: any) => {
  return "function_call" in obj && "reference_key" in obj;
};
const isMethodArgs = (obj: any) => {
  return "function" in obj && "params" in obj && !("module" in obj);
};
const genRanHex = (size: number) =>
  [...Array(size)]
    .map(() => Math.floor(Math.random() * 16).toString(16))
    .join("");
const isModule = (obj: Record<string, any>) => {
  const moduleProperties = ["module"];
  const objKeys = Object.keys(obj);
  return moduleProperties.every((val) => objKeys.includes(val));
};
const isSimpleType = (obj: any) => {
  return (
    typeof obj === "string" ||
    typeof obj === "number" ||
    typeof obj === "boolean" ||
    obj === null
  );
};
