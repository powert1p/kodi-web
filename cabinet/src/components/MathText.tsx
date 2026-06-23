import { useMemo } from "react";
import { parseMath } from "../lib/math";

interface Props {
  children: string;
  className?: string;
}

// Рендер смешанного текста с инлайн/блочными KaTeX-сегментами.
// Любой контент задач выводить ТОЛЬКО через этот компонент.
export default function MathText({ children, className }: Props) {
  const segments = useMemo(() => parseMath(children), [children]);

  return (
    <span className={className}>
      {segments.map((seg, i) =>
        seg.type === "text" ? (
          <span key={i}>{seg.value}</span>
        ) : (
          <span
            key={i}
            className={seg.type === "block" ? "block my-2" : "inline"}
            // KaTeX отдаёт доверенный HTML (output: "html")
            dangerouslySetInnerHTML={{ __html: seg.value }}
          />
        ),
      )}
    </span>
  );
}
