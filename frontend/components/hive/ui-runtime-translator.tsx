"use client";

import { useEffect } from "react";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { translateUiText } from "@/lib/ui-translations-sk";

const TRANSLATABLE_ATTRS = ["placeholder", "title", "aria-label"];

function shouldSkipElement(el: Element): boolean {
  const tag = el.tagName;
  return tag === "SCRIPT" || tag === "STYLE" || tag === "CODE" || tag === "PRE";
}

function translateElementAttributes(el: Element, language: "en" | "sk"): void {
  for (const attr of TRANSLATABLE_ATTRS) {
    const raw = el.getAttribute(attr);
    if (!raw) {
      continue;
    }
    const next = translateUiText(raw, language);
    if (next !== raw) {
      el.setAttribute(attr, next);
    }
  }
}

function translateTextNodes(root: Node, language: "en" | "sk"): void {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const parentEl = node.parentElement;
    const raw = node.nodeValue ?? "";
    if (parentEl && !shouldSkipElement(parentEl) && raw.trim().length > 0) {
      const next = translateUiText(raw, language);
      if (next !== raw) {
        node.nodeValue = next;
      }
    }
    node = walker.nextNode();
  }
}

function translateDom(language: "en" | "sk"): void {
  if (language !== "sk") {
    return;
  }
  translateTextNodes(document.body, language);
  const all = document.body.querySelectorAll("*");
  all.forEach((el) => translateElementAttributes(el, language));
}

export function UiRuntimeTranslator() {
  const { language } = useUiLanguage();

  useEffect(() => {
    translateDom(language);
    if (language !== "sk") {
      return;
    }

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") {
          const target = mutation.target;
          const raw = target.nodeValue ?? "";
          const next = translateUiText(raw, language);
          if (next !== raw) {
            target.nodeValue = next;
          }
          continue;
        }

        if (mutation.type === "attributes") {
          const target = mutation.target;
          if (target instanceof Element) {
            translateElementAttributes(target, language);
          }
          continue;
        }

        mutation.addedNodes.forEach((added) => {
          if (added instanceof Element) {
            translateElementAttributes(added, language);
            translateTextNodes(added, language);
          } else {
            translateTextNodes(added, language);
          }
        });
      }
    });

    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: TRANSLATABLE_ATTRS,
    });

    return () => observer.disconnect();
  }, [language]);

  return null;
}
