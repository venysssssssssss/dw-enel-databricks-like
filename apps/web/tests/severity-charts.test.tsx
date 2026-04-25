import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Sparkline, fmtMoney, fmtN, fmtPct } from "../src/components/bi/SeverityCharts";

describe("SeverityCharts helpers", () => {
  it("formats numbers for pt-BR executive dashboards", () => {
    expect(fmtN(1234567)).toBe("1.234.567");
    expect(fmtMoney(1234.5)).toBe("R$ 1.234,50");
    expect(fmtPct(12.34)).toBe("12,3%");
  });

  it("renders a stable sparkline path", () => {
    const { container } = render(<Sparkline values={[0, 2, 1, 4]} w={40} h={10} />);

    expect(container.querySelector(".sev-spark path")).toHaveAttribute(
      "d",
      "M0.0,10.0 L13.3,5.0 L26.7,7.5 L40.0,0.0"
    );
    expect(container.querySelector(".sev-spark circle")).toHaveAttribute("r", "2");
  });

  it("does not render sparkline markup without values", () => {
    const { container } = render(<Sparkline values={[]} />);

    expect(container.firstChild).toBeNull();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
