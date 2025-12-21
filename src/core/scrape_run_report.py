# scrape_run_report.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import platform
import time
import hashlib


# -----------------------------
# Modelos de reporte (ligeros)
# -----------------------------

@dataclass
class PageAudit:
    page: int
    url: str
    status_code: Optional[int] = None
    items_found: int = 0
    new_items: int = 0
    duration_ms: Optional[int] = None
    note: Optional[str] = None


@dataclass
class StoreRun:
    store: str
    source_mode: str  # "API" | "HTML" | "HEADLESS" (idealmente no)
    category_url: str
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

    pages: List[PageAudit] = field(default_factory=list)

    items_total: int = 0
    items_unique: int = 0
    duplicates: int = 0

    status: str = "UNKNOWN"  # "OK" | "WARN" | "FAIL"
    stop_reason: str = "UNKNOWN"  # ver validator
    error: Optional[str] = None

    def duration_seconds(self) -> float:
        if self.ended_at is None:
            return round(time.time() - self.started_at, 2)
        return round(self.ended_at - self.started_at, 2)


@dataclass
class ScrapeRunReport:
    run_id: str
    category_name: str
    started_at_utc: str
    finished_at_utc: Optional[str] = None
    duration_seconds: Optional[float] = None

    parallel_between_stores: bool = True
    parallel_within_store: bool = False
    headless_used: bool = False

    stores: List[StoreRun] = field(default_factory=list)

    # Auditoría global (opcional, barato)
    total_requests: int = 0
    http_403: int = 0
    http_429: int = 0
    http_5xx: int = 0
    retries: int = 0

    commit: Optional[str] = None
    environment: str = "local"

    def add_store(self, store_run: StoreRun) -> None:
        self.stores.append(store_run)


# -----------------------------
# Reporter + Validator
# -----------------------------

class ScrapeRunReporter:
    """
    Reporter ligero: acumula métricas por tienda y genera un Markdown final.
    Integra "stop_reason" + status para validar 100% A.
    """

    def __init__(
        self,
        category_name: str,
        reports_dir: str = "reports",
        environment: str = "local",
        commit: Optional[str] = None,
        parallel_between_stores: bool = True,
        parallel_within_store: bool = False,
        headless_used: bool = False,
    ):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self._t0 = time.time()
        self.report = ScrapeRunReport(
            run_id=self._make_run_id(category_name),
            category_name=category_name,
            started_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            parallel_between_stores=parallel_between_stores,
            parallel_within_store=parallel_within_store,
            headless_used=headless_used,
            environment=environment,
            commit=commit,
        )

    @staticmethod
    def _make_run_id(category_name: str) -> str:
        raw = f"{category_name}|{datetime.now(timezone.utc).isoformat()}|{os.getpid()}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def store_start(self, store: str, source_mode: str, category_url: str) -> StoreRun:
        s = StoreRun(store=store, source_mode=source_mode, category_url=category_url)
        self.report.add_store(s)
        return s

    def store_page(self, store_run: StoreRun, page_audit: PageAudit) -> None:
        store_run.pages.append(page_audit)
        # Contabiliza requests globales (muy aproximado: 1 request por page_audit)
        self.report.total_requests += 1
        if page_audit.status_code:
            if page_audit.status_code == 403:
                self.report.http_403 += 1
            elif page_audit.status_code == 429:
                self.report.http_429 += 1
            elif 500 <= page_audit.status_code <= 599:
                self.report.http_5xx += 1

    def store_end(
        self,
        store_run: StoreRun,
        items_total: int,
        items_unique: int,
        stop_reason: str,
        status: str = "OK",
        error: Optional[str] = None,
        duplicates: Optional[int] = None,
    ) -> None:
        store_run.ended_at = time.time()
        store_run.items_total = items_total
        store_run.items_unique = items_unique
        store_run.duplicates = duplicates if duplicates is not None else max(items_total - items_unique, 0)
        store_run.stop_reason = stop_reason
        store_run.status = status
        store_run.error = error

    def finalize(self) -> Path:
        t1 = time.time()
        self.report.finished_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.report.duration_seconds = round(t1 - self._t0, 2)

        # Validación automática
        validator = CompletenessValidator()
        validation = validator.validate(self.report)

        # Render
        md = render_markdown_report(self.report, validation)

        # Persistencia
        filename = f"scrape_run_{self.report.run_id}.md"
        out_path = self.reports_dir / filename
        out_path.write_text(md, encoding="utf-8")
        return out_path


class CompletenessValidator:
    """
    Valida “100% A” con heurísticas simples:
    - Debe existir una condición de parada "válida"
    - No debe haber 0 items (salvo categoría realmente vacía)
    - Si hay señales de bloqueo (403/429) -> WARN/FAIL
    """
    VALID_STOP_REASONS = {
        "API_EMPTY",          # API devolvió lista vacía
        "NO_ITEMS_PAGE",      # HTML: página sin items => fin
        "NO_NEW_ITEMS",       # HTML: no aparecen nuevos links => fin
        "TOTAL_PAGES_REACHED" # si se pudo inferir total_pages
    }

    def validate(self, report: ScrapeRunReport) -> Dict[str, Any]:
        per_store = []
        ok_count = 0
        warn_count = 0
        fail_count = 0

        for s in report.stores:
            store_ok = True
            reasons = []

            if s.items_unique <= 0:
                store_ok = False
                reasons.append("SIN_ITEMS")

            if s.stop_reason not in self.VALID_STOP_REASONS:
                # No necesariamente FAIL (puede ser WARN si hubo salida controlada)
                reasons.append(f"STOP_NO_VALIDO:{s.stop_reason}")
                store_ok = False

            if s.error:
                reasons.append("ERROR")
                store_ok = False

            # Señales anti-bloqueo globales (suave)
            if report.http_403 > 0 or report.http_429 > 0:
                reasons.append("POTENCIAL_BLOQUEO")
                # No siempre FAIL; depende de si aún así hay items y parada válida

            # Clasificación final por tienda
            if store_ok:
                status = "OK"
                ok_count += 1
            else:
                # Si hay items pero señales dudosas -> WARN
                if s.items_unique > 0 and ("POTENCIAL_BLOQUEO" in reasons or any(r.startswith("STOP_NO_VALIDO") for r in reasons)):
                    status = "WARN"
                    warn_count += 1
                else:
                    status = "FAIL"
                    fail_count += 1

            per_store.append({
                "store": s.store,
                "status": status,
                "items_unique": s.items_unique,
                "stop_reason": s.stop_reason,
                "reasons": reasons,
            })

        # Estado global
        if fail_count > 0:
            global_status = "INCOMPLETO"
        elif warn_count > 0:
            global_status = "COMPLETO_CON_INCIDENTES"
        else:
            global_status = "COMPLETO"

        return {
            "global_status": global_status,
            "ok_count": ok_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "per_store": per_store
        }


# -----------------------------
# Render Markdown
# -----------------------------

def render_markdown_report(report: ScrapeRunReport, validation: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append(f"# Scrape Run Report — {report.category_name}")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(f"- **Run ID:** `{report.run_id}`")
    lines.append(f"- **Inicio:** {report.started_at_utc}")
    lines.append(f"- **Fin:** {report.finished_at_utc}")
    lines.append(f"- **Duración total:** {report.duration_seconds} s")
    lines.append(f"- **Ejecución paralela entre webs:** {'Sí' if report.parallel_between_stores else 'No'}")
    lines.append(f"- **Paralelo interno por páginas:** {'Sí' if report.parallel_within_store else 'No'}")
    lines.append(f"- **Headless usado:** {'Sí' if report.headless_used else 'No'}")
    lines.append(f"- **Resultado global:** **{validation['global_status']}**")
    lines.append("")

    lines.append("## 2. Definición aplicada (100% A)")
    lines.append("")
    lines.append("> 100% A = todos los productos visibles en la categoría (sin filtros), recorriendo todas las páginas/cargas hasta condición de parada válida.")
    lines.append("")

    lines.append("## 3. Resumen por web (vista rápida)")
    lines.append("")
    lines.append("| Web | Fuente | Páginas | Items | Duplicados | Tiempo (s) | Stop reason | Estado |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---|")

    # Map store -> validation status
    vmap = {x["store"]: x["status"] for x in validation["per_store"]}

    for s in report.stores:
        lines.append(
            f"| {s.store} | {s.source_mode} | {len(s.pages) if s.pages else '—'} | {s.items_unique} | {s.duplicates} | {s.duration_seconds()} | {s.stop_reason} | {vmap.get(s.store, s.status)} |"
        )
    lines.append("")

    lines.append("## 4. Auditoría global")
    lines.append("")
    lines.append(f"- Requests totales (aprox.): **{report.total_requests}**")
    lines.append(f"- HTTP 403: **{report.http_403}**")
    lines.append(f"- HTTP 429: **{report.http_429}**")
    lines.append(f"- HTTP 5xx: **{report.http_5xx}**")
    lines.append(f"- Retries: **{report.retries}**")
    lines.append("")

    lines.append("## 5. Detalle por web")
    lines.append("")
    for s in report.stores:
        lines.append(f"### 5.{report.stores.index(s)+1} {s.store}")
        lines.append("")
        lines.append(f"- **URL categoría:** {s.category_url}")
        lines.append(f"- **Fuente:** {s.source_mode}")
        lines.append(f"- **Items únicos:** {s.items_unique}")
        lines.append(f"- **Duplicados:** {s.duplicates}")
        lines.append(f"- **Tiempo:** {s.duration_seconds()} s")
        lines.append(f"- **Stop reason:** {s.stop_reason}")
        if s.error:
            lines.append(f"- **Error:** `{s.error}`")
        lines.append("")

        if s.pages:
            lines.append("**Auditoría por página**")
            lines.append("")
            lines.append("| Página | Items | Nuevos | Status | Duración (ms) | URL | Nota |")
            lines.append("|---:|---:|---:|---:|---:|---|---|")
            for p in s.pages:
                lines.append(
                    f"| {p.page} | {p.items_found} | {p.new_items} | {p.status_code or '—'} | {p.duration_ms or '—'} | {p.url} | {p.note or ''} |"
                )
            lines.append("")

    lines.append("## 6. Huella de ejecución")
    lines.append("")
    lines.append(f"- Commit: `{report.commit or 'N/A'}`")
    lines.append(f"- Entorno: `{report.environment}`")
    lines.append(f"- Plataforma: `{platform.platform()}`")
    lines.append("")
    return "\n".join(lines)