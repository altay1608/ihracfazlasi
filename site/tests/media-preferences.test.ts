import assert from "node:assert/strict";
import { test } from "node:test";
import { shouldLoadDecorativeVideo } from "../lib/media-preferences";

test("decorative videos respect mobile/reduced-motion, slow connections and data saving", () => {
  const oldWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  const oldNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  try {
    for (const scenario of [
      { matches: true, connection: undefined, expected: false },
      { matches: false, connection: { saveData: true }, expected: false },
      { matches: false, connection: { effectiveType: "3g" }, expected: false },
      { matches: false, connection: { effectiveType: "2g" }, expected: false },
      { matches: false, connection: { effectiveType: "4g" }, expected: true },
      { matches: false, connection: undefined, expected: true },
    ]) {
      Object.defineProperty(globalThis, "window", { configurable: true, value: { matchMedia: () => ({ matches: scenario.matches }) } });
      Object.defineProperty(globalThis, "navigator", { configurable: true, value: { connection: scenario.connection } });
      assert.equal(shouldLoadDecorativeVideo(), scenario.expected);
    }
  } finally {
    if (oldWindow) Object.defineProperty(globalThis, "window", oldWindow);
    else Reflect.deleteProperty(globalThis, "window");
    if (oldNavigator) Object.defineProperty(globalThis, "navigator", oldNavigator);
    else Reflect.deleteProperty(globalThis, "navigator");
  }
});
