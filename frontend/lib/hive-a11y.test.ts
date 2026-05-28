/**
 * @vitest-environment happy-dom
 */
import { describe, expect, it } from "vitest";

import {
  getFocusableElements,
  handleFocusTrapKeydown,
  handleHorizontalNavKeydown,
  HIVE_MAIN_CONTENT_ID,
} from "@/lib/hive-a11y";

describe("hive-a11y", () => {
  it("exports main content landmark id", () => {
    expect(HIVE_MAIN_CONTENT_ID).toBe("hive-main-canvas");
  });

  it("collects focusable elements and traps tab forward", () => {
    document.body.innerHTML = `
      <div id="modal">
        <button type="button" id="first">First</button>
        <button type="button" id="last">Last</button>
      </div>
    `;
    const modal = document.getElementById("modal") as HTMLElement;
    const focusable = getFocusableElements(modal);
    expect(focusable).toHaveLength(2);

    const last = document.getElementById("last") as HTMLElement;
    last.focus();

    const event = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    handleFocusTrapKeydown(event, modal);
    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement?.id).toBe("first");
  });

  it("moves focus with arrow keys in subnav rows", () => {
    document.body.innerHTML = `
      <nav id="subnav">
        <button type="button" data-hive-subnav-tab data-hive-subnav-id="a" aria-current="page">A</button>
        <button type="button" data-hive-subnav-tab data-hive-subnav-id="b">B</button>
        <button type="button" data-hive-subnav-tab data-hive-subnav-id="c">C</button>
      </nav>
    `;
    const nav = document.getElementById("subnav") as HTMLElement;
    const activated: string[] = [];
    const first = nav.querySelector<HTMLElement>("[data-hive-subnav-id='a']")!;
    first.focus();

    const event = new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true });
    handleHorizontalNavKeydown(event, nav, (tab) => {
      activated.push(tab.getAttribute("data-hive-subnav-id") ?? "");
    });

    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement?.getAttribute("data-hive-subnav-id")).toBe("b");
    expect(activated).toEqual(["b"]);
  });

  it("traps shift+tab from first element to last", () => {
    document.body.innerHTML = `
      <div id="modal">
        <button type="button" id="first">First</button>
        <button type="button" id="last">Last</button>
      </div>
    `;
    const modal = document.getElementById("modal") as HTMLElement;
    const first = document.getElementById("first") as HTMLElement;
    first.focus();

    const event = new KeyboardEvent("keydown", {
      key: "Tab",
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    handleFocusTrapKeydown(event, modal);
    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement?.id).toBe("last");
  });
});
