import { describe, expect, it } from "vitest";
import { encodeFilters } from "../src/lib/api";

describe("api helpers", () => {
  it("encodes filters as base64url", () => {
    const encoded = encodeFilters({ regiao: ["CE"], status: "ABERTO" });

    expect(encoded).not.toContain("=");
    expect(encoded).not.toContain("+");
    expect(encoded).not.toContain("/");
  });
});
