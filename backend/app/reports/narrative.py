"""سرد مكتوب من الأرقام مباشرة — بلا نموذج لغوي.

يُستخدم عندما يخالف النموذج لغة التقرير أو يعجز عن إخراج نتائج،
فيبقى التقرير مفيداً وبلغة المستخدم مهما ضعف النموذج المحلي.
"""

_T = {
    "ar": {
        "covers": "يغطي هذا التقرير {records} سجلاً من {subject}.",
        "total": "بلغ إجمالي {measure} {total}، بمتوسط {average} لكل سجل، وأعلى قيمة {highest}.",
        "period": "تمتد البيانات من {start} إلى {end}.",
        "rose": "ارتفع {measure} من {first} إلى {last} بنسبة {pct}%.",
        "fell": "انخفض {measure} من {first} إلى {last} بنسبة {pct}%.",
        "steady": "استقر {measure} عند مستوى {last} تقريباً.",
        "peak": "سُجلت الذروة في {label} بقيمة {value}.",
        "leader": "تصدّر «{leader}» في {dim} بقيمة {value} ({pct}% من الإجمالي).",
        "leaderNoPct": "تصدّر «{leader}» في {dim} بقيمة {value}.",
        "spread": "تتوزع البيانات على {count} فئة في {dim}.",
        "recConcentration": "راجع تركّز {pct}% من {measure} في «{leader}» وقيّم مخاطر الاعتماد عليه.",
        "recTrend": "ادرس أسباب تغير {measure} بنسبة {pct}% خلال الفترة.",
        "recDetail": "وسّع البيانات المتاحة لتحليل أعمق (تفاصيل زمنية أو تصنيفات إضافية).",
        "recMonitor": "تابع مؤشرات {measure} دورياً لرصد أي انحراف مبكراً.",
        "of": "البيانات",
    },
    "en": {
        "covers": "This report covers {records} records from {subject}.",
        "total": "Total {measure} reached {total}, averaging {average} per record, with a peak of {highest}.",
        "period": "The data spans {start} to {end}.",
        "rose": "{measure} rose from {first} to {last}, up {pct}%.",
        "fell": "{measure} fell from {first} to {last}, down {pct}%.",
        "steady": "{measure} held steady at about {last}.",
        "peak": "The peak was recorded on {label} at {value}.",
        "leader": "'{leader}' leads {dim} with {value} ({pct}% of the total).",
        "leaderNoPct": "'{leader}' leads {dim} with {value}.",
        "spread": "The data spreads across {count} categories in {dim}.",
        "recConcentration": "Review the {pct}% concentration of {measure} in '{leader}' and assess dependency risk.",
        "recTrend": "Investigate what drove the {pct}% change in {measure} over the period.",
        "recDetail": "Broaden the data available for deeper analysis (finer dates or extra categories).",
        "recMonitor": "Track {measure} regularly to catch deviations early.",
        "of": "the data",
    },
}


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{value:,}"


def compose_narrative(business: dict, labels: dict, language: str,
                      subject: str = "") -> dict:
    """يبني ملخصاً ونتائج وتوصيات من أرقام الأعمال المحسوبة."""
    t = _T.get(language, _T["en"])
    lbl = lambda c: labels.get(c, c) if c else ""          # noqa: E731
    multi = len(business) > 1

    summary_parts, findings, recommendations = [], [], []
    total_records = 0

    for table, b in business.items():
        prefix = f"{lbl(table)}: " if multi else ""
        kpis = {k["key"]: k for k in b["kpis"]}
        measure_col = next((k.get("column") for k in b["kpis"] if k.get("column")), None)
        measure = lbl(measure_col) if measure_col else ""
        total_records += kpis.get("records", {}).get("value", 0) or 0

        if measure and "total" in kpis:
            line = t["total"].format(
                measure=measure, total=_fmt(kpis["total"]["value"]),
                average=_fmt(kpis["average"]["value"]),
                highest=_fmt(kpis["highest"]["value"]))
            findings.append(prefix + line)
            if not multi:
                summary_parts.append(line)

        tr = b.get("trend")
        if tr:
            if not multi:
                summary_parts.append(t["period"].format(
                    start=tr["period"][0], end=tr["period"][1]))
            pct = tr.get("change_pct")
            if pct is None or abs(pct) < 1:
                findings.append(prefix + t["steady"].format(
                    measure=measure or t["of"], last=_fmt(tr["last"])))
            else:
                key = "rose" if pct > 0 else "fell"
                findings.append(prefix + t[key].format(
                    measure=measure or t["of"], first=_fmt(tr["first"]),
                    last=_fmt(tr["last"]), pct=_fmt(abs(pct))))
                recommendations.append(t["recTrend"].format(
                    measure=measure or t["of"], pct=_fmt(abs(pct))))
            findings.append(prefix + t["peak"].format(
                label=tr["peak_label"], value=_fmt(tr["peak_value"])))

        for bd in b.get("breakdowns", [])[:2]:
            dim = lbl(bd["column"])
            if bd.get("leader_share_pct") is not None:
                findings.append(prefix + t["leader"].format(
                    leader=bd["leader"], dim=dim, value=_fmt(bd["leader_value"]),
                    pct=_fmt(bd["leader_share_pct"])))
                if bd["leader_share_pct"] >= 50 and measure:
                    recommendations.append(t["recConcentration"].format(
                        pct=_fmt(bd["leader_share_pct"]), measure=measure,
                        leader=bd["leader"]))
            else:
                findings.append(prefix + t["leaderNoPct"].format(
                    leader=bd["leader"], dim=dim, value=_fmt(bd["leader_value"])))
            findings.append(prefix + t["spread"].format(
                count=bd["categories"], dim=dim))

    summary = " ".join(
        [t["covers"].format(records=_fmt(total_records),
                            subject=subject or t["of"])] + summary_parts[:2])

    if not recommendations:
        recommendations.append(t["recDetail"])
    measures = [lbl(k.get("column")) for b in business.values()
                for k in b["kpis"] if k.get("column")]
    if measures:
        recommendations.append(t["recMonitor"].format(measure=measures[0]))

    return {"summary": summary, "findings": findings[:8],
            "recommendations": recommendations[:4]}
