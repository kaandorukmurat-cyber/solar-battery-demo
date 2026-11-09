"""Solar + Battery Planner: interactive demo (Python / Streamlit).

Run on your computer:   streamlit run streamlit_app.py
Share with a public link: deploy this folder free on Streamlit Community Cloud (see README.md).
"""
import pandas as pd
import streamlit as st

import demo_core as core

st.set_page_config(page_title="Solar + Battery Planner", page_icon="☀️", layout="wide")

T = {
    "en": dict(
        title="Solar + Battery Planner",
        sub="26 MW solar park · battery option · market-linked PPC contract with a daily minimum",
        tab_day="One day", tab_year="A full year", scenario="Day", battery="Battery",
        none_today="None (today)", pays="PPC pays", market="Market price (today)", fixed="Fixed price",
        fixed_price="Fixed PPC price (€/MWh)", peak="Peak agreement 17:00–22:00", peak_none="None (today)",
        peak_fixed="Fixed evening price", peak_price="Evening price (€/MWh)", avg="Tomorrow's day-ahead average (€/MWh)",
        minimum="PPC daily minimum (MWh)", penalty="Penalty per MWh short (€)",
        solo="Solar only", rule="Simple battery rule", planner="With the planner", day="The day",
        solo_d="No battery: sell the sun when it shines", rule_d="Charge 11–15h, discharge 18–22h",
        needs="Needs a battery", vs_rule="vs the simple rule", sun="of sun forecast",
        short="MWh short of the minimum (penalty {p})", met="PPC minimum met",
        story_batt="The planner stores **{a:,.0f} MWh** of solar while it is worth little, buys **{b:,.0f} MWh** from the grid when it costs less than it can be resold for, and sells **{c:,.0f} MWh** from the battery when prices are highest.",
        story_none="Without a battery the park can only sell when the sun shines.",
        wx="Weather forecast for tomorrow at the site", wx_src="MET Norway forecast (CC BY 4.0), issued 9 Nov 2026 07:16 UTC",
        hour="Hour", sky="Sky", low="Low cloud %", mid="Mid cloud %", high="High cloud %", temp="°C",
        wx_line="Forecast output **{a:,.0f} MWh** (a cloudless day would give {b:,.0f} MWh) · cloudy case **{c:,.0f} MWh** · PPC minimum **{d:,.0f} MWh**",
        shortfall="Expected shortfall against the PPC minimum.",
        ch_power="What the planner does with each 15 minutes (MW; below 0 = charging)",
        ch_price="Market price and what PPC pays (€/MWh)", ch_soc="Battery charge (MWh)",
        c_solar="Solar → PPC", c_batt="Battery → PPC", c_sb="Solar → battery", c_gb="Grid → battery", c_curt="Curtailed",
        c_market="Day-ahead market (modelled)", c_ppc="PPC pays",
        level="Price level", y2026="2026 so far (avg ~€152)", y2025="2025 (avg €108)", capex="Battery cost (€ thousand per MWh)",
        a_year="a year", gwh="GWh of solar", payback="Battery payback", yrs="years", build="to build",
        per_year="a year with the planner", month_chart="Margin by month (€ thousand)",
        size_table="Battery size: what each strategy earns per year", col_batt="Battery", col_planner="Planner",
        col_adds="Planner adds", year_note="Today's contract: PPC pays the day-ahead price at every hour, no peak agreement. Margin after PPC fees, grid purchases, battery wear (€15/MWh discharged) and shortfall penalties. Battery cost covers the build only.",
        months=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        specs="Battery specs (optional)", custom_cap="Custom capacity", cap="Capacity (MWh)",
        dur="Duration (hours at full power)", rte="Round-trip efficiency (%)", wear="Wear cost per MWh discharged (€)",
        reserve="Minimum reserve (%)", start="Charge at start of day (%)", end="Target charge at end of day (%)",
        power="Power: **{p:.1f} MW** · usable **{c:.0f} MWh**",
        specs_note="Applies to the One day tab. The Full year tab uses the standard battery (2-hour, 88%, €15/MWh wear, 5% reserve, 20% start and end).",
        ybatt="Battery (standard specs)",
        foot="Illustrative model, not a forecast of returns. Prices are modelled 15-minute curves scaled to Romania's publicly reported monthly day-ahead averages (OPCOM, via press); they are not exchange data. Minimum = 60% of the month's typical daily output, penalty €50/MWh unless changed, grid purchases don't count toward the minimum. Site: 30 MWp / 26 MW AC, southern Romania. Battery: 2-hour, 88% round trip, €15/MWh wear as standard; other specs can be set under Battery specs (One day tab only). Tomorrow's weather: MET Norway Locationforecast (CC BY 4.0), converted to site output by the planner's cloud-layer model.",
        lang="Language",
    ),
    "tr": dict(
        title="Güneş + Batarya Planlayıcı",
        sub="26 MW güneş santrali · batarya seçeneği · günlük asgari teslimatlı, piyasa fiyatına bağlı PPC sözleşmesi",
        tab_day="Bir gün", tab_year="Tam bir yıl", scenario="Gün", battery="Batarya",
        none_today="Yok (bugün)", pays="PPC ödemesi", market="Piyasa fiyatı (bugün)", fixed="Sabit fiyat",
        fixed_price="Sabit PPC fiyatı (€/MWh)", peak="Pik anlaşması 17:00–22:00", peak_none="Yok (bugün)",
        peak_fixed="Sabit akşam fiyatı", peak_price="Akşam fiyatı (€/MWh)", avg="Yarının gün öncesi ortalaması (€/MWh)",
        minimum="PPC günlük asgari teslimat (MWh)", penalty="Eksik MWh başına ceza (€)",
        solo="Yalnızca güneş", rule="Basit batarya kuralı", planner="Planlayıcı ile", day="Gün",
        solo_d="Batarya yok: güneş varken sat", rule_d="11–15 arası şarj, 18–22 arası boşalt",
        needs="Batarya gerekir", vs_rule="basit kurala göre", sun="güneş tahmini",
        short="MWh asgarinin altında (ceza {p})", met="PPC asgarisi karşılandı",
        story_batt="Planlayıcı, güneş enerjisi ucuzken **{a:,.0f} MWh** depoluyor, satış fiyatından ucuz olduğu saatlerde şebekeden **{b:,.0f} MWh** alıyor ve fiyatların en yüksek olduğu saatlerde bataryadan **{c:,.0f} MWh** satıyor.",
        story_none="Batarya olmadan santral yalnızca güneş varken satış yapabilir.",
        wx="Santral için yarının hava tahmini", wx_src="MET Norway tahmini (CC BY 4.0), 9 Kasım 2026 07:16 UTC yayımı",
        hour="Saat", sky="Gökyüzü", low="Alçak bulut %", mid="Orta bulut %", high="Yüksek bulut %", temp="°C",
        wx_line="Tahmini üretim **{a:,.0f} MWh** (bulutsuz bir gün {b:,.0f} MWh verirdi) · bulutlu senaryo **{c:,.0f} MWh** · PPC asgarisi **{d:,.0f} MWh**",
        shortfall="PPC asgarisine göre açık bekleniyor.",
        ch_power="Planlayıcının her 15 dakikada yaptığı (MW; 0’ın altı = şarj)",
        ch_price="Piyasa fiyatı ve PPC ödemesi (€/MWh)", ch_soc="Batarya doluluğu (MWh)",
        c_solar="Güneş → PPC", c_batt="Batarya → PPC", c_sb="Güneş → batarya", c_gb="Şebeke → batarya", c_curt="Kısıtlanan",
        c_market="Gün öncesi piyasa (modellenmiş)", c_ppc="PPC ödemesi",
        level="Fiyat seviyesi", y2026="2026 bugüne kadar (ort. ~152 €)", y2025="2025 (ort. 108 €)", capex="Batarya maliyeti (MWh başına bin €)",
        a_year="yıllık", gwh="GWh güneş", payback="Batarya geri ödeme süresi", yrs="yıl", build="kurulum",
        per_year="planlayıcıyla yıllık kazanç", month_chart="Aylık marj (bin €)",
        size_table="Batarya boyutu: her stratejinin yıllık kazancı", col_batt="Batarya", col_planner="Planlayıcı",
        col_adds="Planlayıcı katkısı", year_note="Bugünkü sözleşme: PPC her saat gün öncesi fiyatı öder, pik anlaşması yok. Marj; PPC ücretleri, şebeke alımları, batarya aşınması (boşaltılan MWh başına 15 €) ve eksik teslimat cezaları düşülmüş haldedir. Batarya maliyeti yalnızca kurulumu kapsar.",
        months=["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
        specs="Batarya özellikleri (isteğe bağlı)", custom_cap="Özel kapasite", cap="Kapasite (MWh)",
        dur="Süre (tam güçte saat)", rte="Çevrim verimi (%)", wear="Boşaltılan MWh başına aşınma maliyeti (€)",
        reserve="Minimum rezerv (%)", start="Gün başı doluluk (%)", end="Gün sonu hedef doluluk (%)",
        power="Güç: **{p:.1f} MW** · kullanılabilir **{c:.0f} MWh**",
        specs_note="Yalnızca Bir gün sekmesine uygulanır. Tam bir yıl sekmesi standart bataryayı kullanır (2 saatlik, %88, MWh başına 15 € aşınma, %5 rezerv, başta ve sonda %20).",
        ybatt="Batarya (standart özellikler)",
        foot="Örnek modeldir, getiri tahmini değildir. Fiyatlar, Romanya’nın kamuya açıklanan aylık gün öncesi ortalamalarına (OPCOM, basın aracılığıyla) ölçeklenmiş modellenmiş 15 dakikalık eğrilerdir; borsa verisi değildir. Asgari = ayın tipik günlük üretiminin %60’ı, değiştirilmedikçe ceza 50 €/MWh, şebeke alımları asgariye sayılmaz. Santral: 30 MWp / 26 MW AC, Güney Romanya. Batarya: standart olarak 2 saatlik, %88 çevrim verimi, MWh başına 15 € aşınma; diğer özellikler Batarya özellikleri bölümünden ayarlanabilir (yalnızca Bir gün sekmesi). Yarının havası: MET Norway Locationforecast (CC BY 4.0), planlayıcının bulut katmanı modeliyle santral üretimine çevrildi.",
        lang="Dil",
    ),
}
SKY = {"en": dict(fog="Fog", cloudy="Cloudy", partlycloudy_day="Partly cloudy", partlycloudy_night="Partly cloudy",
                  fair_day="Fair", fair_night="Fair", clearsky_day="Clear", lightrain="Light rain", rain="Rain"),
       "tr": dict(fog="Sis", cloudy="Bulutlu", partlycloudy_day="Parçalı bulutlu", partlycloudy_night="Parçalı bulutlu",
                  fair_day="Az bulutlu", fair_night="Az bulutlu", clearsky_day="Açık", lightrain="Hafif yağmur", rain="Yağmur")}

lang = st.sidebar.radio("Language / Dil", ["tr", "en"], format_func=lambda x: "Türkçe" if x == "tr" else "English", horizontal=True)
L = T[lang]


def eur(v: float) -> str:
    s = f"{abs(v):,.0f}"
    s = s.replace(",", ".") + " €" if lang == "tr" else "€" + s
    return ("−" if v < 0 else "") + s


def eur_m(v: float) -> str:
    s = f"{abs(v) / 1e6:,.2f}"
    s = (s.replace(".", ",") + " milyon €") if lang == "tr" else ("€" + s + "M")
    return ("−" if v < 0 else "") + s


def eur_k(v: float) -> str:
    s = f"{abs(v) / 1e3:,.0f}"
    s = (s.replace(",", ".") + " bin €") if lang == "tr" else ("€" + s + "k")
    return ("−" if v < 0 else "") + s


def num(v: float, d: int = 0) -> str:
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "tr" else s


st.title(L["title"])
st.caption(L["sub"])
tab_day, tab_year = st.tabs([L["tab_day"], L["tab_year"]])

# ------------------------------------------------------------------ one day
with tab_day:
    keys = list(core.SCENARIOS)
    key = st.radio(L["scenario"], keys, horizontal=True,
                   format_func=lambda k: core.SCENARIOS[k][f"title_{lang}"])
    sc = core.SCENARIOS[key]
    st.caption(sc[f"blurb_{lang}"])

    c1, c2, c3 = st.columns(3)
    with c1:
        batt = st.radio(L["battery"], core.BATTERIES, horizontal=True,
                        format_func=lambda b: L["none_today"] if b == 0 else f"{b} MWh")
        if key == "live":
            day_avg = st.slider(L["avg"], 100, 500, 305, 5)
        else:
            day_avg = None
    with c2:
        pay_rule = st.radio(L["pays"], ["market", "fixed"], horizontal=True,
                            format_func=lambda r: L["market"] if r == "market" else L["fixed"])
        fixed_price = st.slider(L["fixed_price"], 40, 310, 305, 5, disabled=pay_rule == "market")
        peak = st.radio(L["peak"], [False, True], horizontal=True,
                        format_func=lambda p: L["peak_fixed"] if p else L["peak_none"])
        peak_price = st.slider(L["peak_price"], 100, 400, 305, 5, disabled=not peak)
    with c3:
        min_mwh = st.slider(L["minimum"], 0, 160, int(round(sc["min"])), 1, key=f"min_{key}")
        penalty = st.slider(L["penalty"], 0, 300, 50, 10)

    std = core.STANDARD_SPECS
    with st.expander(L["specs"]):
        e1, e2, e3 = st.columns(3)
        with e1:
            custom = st.checkbox(L["custom_cap"], key="custom_cap")
            cap = st.slider(L["cap"], 2, 80, batt or 20, 1, disabled=not custom, key="cap")
            dur = st.select_slider(L["dur"], [1.0, 1.5, 2.0, 3.0, 4.0], std["duration_h"], key="dur")
        with e2:
            rte = st.slider(L["rte"], 75, 95, int(std["rte_pct"]), 1, key="rte")
            wear = st.slider(L["wear"], 0, 40, int(std["wear"]), 1, key="wear")
        with e3:
            reserve = st.slider(L["reserve"], 0, 30, int(std["reserve_pct"]), 1, key="reserve")
            start = st.slider(L["start"], 0, 90, int(std["start_pct"]), 5, key="start")
            end = st.slider(L["end"], 0, 90, int(std["end_pct"]), 5, key="end")
        if custom:
            batt = cap
        if batt:
            st.markdown(L["power"].format(p=batt / dur, c=batt))
        st.caption(L["specs_note"])
    specs = dict(duration_h=float(dur), rte_pct=float(rte), wear=float(wear),
                 reserve_pct=float(reserve), start_pct=float(start), end_pct=float(end))

    r = core.run_day(key, batt, pay_rule, fixed_price, peak, peak_price, min_mwh, penalty, day_avg, specs)
    solo, rule, plan = r["solar_only"], r["simple_rule"], r["planner"]

    if batt:
        st.info(L["story_batt"].format(a=r["stored_mwh"], b=r["bought_mwh"], c=r["sold_from_battery_mwh"]))
    else:
        st.info(L["story_none"])

    if key == "live":
        st.subheader(L["wx"])
        st.caption(L["wx_src"])
        wx = pd.DataFrame([{L["hour"]: h["h"], L["sky"]: SKY[lang].get(h["sym"], h["sym"]),
                            L["low"]: round(h["low"]), L["mid"]: round(h["mid"]), L["high"]: round(h["high"]),
                            L["temp"]: round(h["temp"])} for h in sc["hours"]]).set_index(L["hour"])
        st.dataframe(wx.T.astype(str), use_container_width=True)
        clear_mwh = sum(sc["clear"]) * 0.25
        st.markdown(L["wx_line"].format(a=r["solar_mwh"], b=clear_mwh, c=r["solar_mwh"] * 0.7, d=r["min_mwh"]))
        if r["solar_mwh"] < r["min_mwh"]:
            st.warning(L["shortfall"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(L["solo"], eur(solo["margin"]), help=L["solo_d"])
    m2.metric(L["rule"], eur(rule["margin"]) if rule else "–", help=L["rule_d"] if rule else L["needs"])
    m3.metric(L["planner"], eur(plan["margin"]),
              delta=(eur(plan["margin"] - rule["margin"]) + " " + L["vs_rule"]) if rule else None)
    m4.metric(L["day"], f"{num(r['solar_mwh'])} MWh",
              help=f"{L['sun']} · {num(r['price_min'])}–{num(r['price_max'])} €/MWh")
    if plan["short"] > 0.05:
        st.warning(f"{num(plan['short'], 1)} " + L["short"].format(p=eur(plan["penalty"])))
    else:
        st.success(L["met"])

    tb = r["table"].set_index("time")
    st.subheader(L["ch_power"])
    st.bar_chart(tb[["solar_to_ppc_mw", "battery_to_ppc_mw", "solar_to_battery_mw", "grid_to_battery_mw", "curtailed_mw"]]
                 .rename(columns={"solar_to_ppc_mw": L["c_solar"], "battery_to_ppc_mw": L["c_batt"],
                                  "solar_to_battery_mw": L["c_sb"], "grid_to_battery_mw": L["c_gb"], "curtailed_mw": L["c_curt"]}),
                 color=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"], height=300)
    g1, g2 = st.columns([3, 2])
    with g1:
        st.subheader(L["ch_price"])
        st.line_chart(tb[["market_eur_mwh", "ppc_pays_eur_mwh"]].rename(
            columns={"market_eur_mwh": L["c_market"], "ppc_pays_eur_mwh": L["c_ppc"]}), color=["#2a78d6", "#eda100"], height=240)
    with g2:
        st.subheader(L["ch_soc"])
        if not batt:
            st.caption(L["needs"])
        else:
          st.area_chart(tb[["battery_mwh"]].rename(columns={"battery_mwh": L["ch_soc"]}), color=["#2a78d6"], height=240)

# ------------------------------------------------------------------ full year
with tab_year:
    y1, y2, y3 = st.columns(3)
    with y1:
        lvl = st.radio(L["level"], ["2026", "2025"], horizontal=True, format_func=lambda v: L["y" + v])
    with y2:
        ybatt = st.radio(L["ybatt"], core.BATTERIES, index=2, horizontal=True, key="ybatt",
                         format_func=lambda b: L["none_today"] if b == 0 else f"{b} MWh")
    with y3:
        capex = st.slider(L["capex"], 150, 350, 220, 10)

    base, Y = core.year(0, lvl), core.year(ybatt, lvl)
    solo_y, rule_y, plan_y, perf_y = (base["year"]["solar-only"], Y["year"]["simple rule"],
                                     Y["year"]["planner"], Y["year"]["perfect"])
    gain = plan_y - solo_y
    build = capex * 1000 * ybatt
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(L["solo"], eur_m(solo_y), help=f"{L['a_year']} · {num(base['solar'] / 1000, 1)} {L['gwh']}")
    k2.metric(L["rule"], eur_m(rule_y) if ybatt else "–")
    k3.metric(L["planner"], eur_m(plan_y),
              delta=(eur_k(plan_y - rule_y) + " " + L["vs_rule"]) if ybatt else None)
    k4.metric(L["payback"], f"{num(build / gain, 1)} {L['yrs']}" if ybatt and gain > 0 else "–",
              help=f"{eur_m(build)} {L['build']} · {eur_k(gain)} {L['per_year']}" if ybatt else None)

    months = sorted(Y["monthly"], key=int)
    mdf = pd.DataFrame({
        L["solo"]: [base["monthly"][m]["solar-only"] / 1000 for m in months],
        L["rule"]: [Y["monthly"][m]["simple rule"] / 1000 if ybatt else 0 for m in months],
        L["col_planner"]: [Y["monthly"][m]["planner"] / 1000 for m in months],
    }, index=pd.Index([f"{int(m):02d} {L['months'][int(m) - 1]}" for m in months]))
    st.subheader(L["month_chart"])
    st.bar_chart(mdf, stack=False, color=["#7a7972", "#eb6834", "#2a78d6"], height=320)

    st.subheader(L["size_table"])
    rows = []
    for b in core.BATTERIES:
        Z = core.year(b, lvl)
        rows.append({L["col_batt"]: L["none_today"] if b == 0 else f"{b} MWh",
                     L["rule"]: eur_m(Z["year"]["simple rule"]), L["col_planner"]: eur_m(Z["year"]["planner"]),
                     L["col_adds"]: ("+" + eur_k(Z["year"]["planner"] - Z["year"]["simple rule"])) if b else "–"})
    st.dataframe(pd.DataFrame(rows).set_index(L["col_batt"]), use_container_width=True)
    st.caption(L["year_note"])

st.divider()
st.caption(L["foot"])
"""Solar + Battery Planner: interactive demo (Python / Streamlit).

Run on your computer:   streamlit run streamlit_app.py
Share with a public link: deploy this folder free on Streamlit Community Cloud (see README.md).
"""
import pandas as pd
import streamlit as st

import demo_core as core

st.set_page_config(page_title="Solar + Battery Planner", page_icon="☀️", layout="wide")

T = {
    "en": dict(
        title="Solar + Battery Planner",
        sub="26 MW solar park · battery option · market-linked PPC contract with a daily minimum",
        tab_day="One day", tab_year="A full year", scenario="Day", battery="Battery",
        none_today="None (today)", pays="PPC pays", market="Market price (today)", fixed="Fixed price",
        fixed_price="Fixed PPC price (€/MWh)", peak="Peak agreement 17:00–22:00", peak_none="None (today)",
        peak_fixed="Fixed evening price", peak_price="Evening price (€/MWh)", avg="Tomorrow's day-ahead average (€/MWh)",
        minimum="PPC daily minimum (MWh)", penalty="Penalty per MWh short (€)",
        solo="Solar only", rule="Simple battery rule", planner="With the planner", day="The day",
        solo_d="No battery: sell the sun when it shines", rule_d="Charge 11–15h, discharge 18–22h",
        needs="Needs a battery", vs_rule="vs the simple rule", sun="of sun forecast",
        short="MWh short of the minimum (penalty {p})", met="PPC minimum met",
        story_batt="The planner stores **{a:,.0f} MWh** of solar while it is worth little, buys **{b:,.0f} MWh** from the grid when it costs less than it can be resold for, and sells **{c:,.0f} MWh** from the battery when prices are highest.",
        story_none="Without a battery the park can only sell when the sun shines.",
        wx="Weather forecast for tomorrow at the site", wx_src="MET Norway forecast (CC BY 4.0), issued 9 Nov 2026 07:16 UTC",
        hour="Hour", sky="Sky", low="Low cloud %", mid="Mid cloud %", high="High cloud %", temp="°C",
        wx_line="Forecast output **{a:,.0f} MWh** (a cloudless day would give {b:,.0f} MWh) · cloudy case **{c:,.0f} MWh** · PPC minimum **{d:,.0f} MWh**",
        shortfall="Expected shortfall against the PPC minimum.",
        ch_power="What the planner does with each 15 minutes (MW; below 0 = charging)",
        ch_price="Market price and what PPC pays (€/MWh)", ch_soc="Battery charge (MWh)",
        c_solar="Solar → PPC", c_batt="Battery → PPC", c_sb="Solar → battery", c_gb="Grid → battery", c_curt="Curtailed",
        c_market="Day-ahead market (modelled)", c_ppc="PPC pays",
        level="Price level", y2026="2026 so far (avg ~€152)", y2025="2025 (avg €108)", capex="Battery cost (€ thousand per MWh)",
        a_year="a year", gwh="GWh of solar", payback="Battery payback", yrs="years", build="to build",
        per_year="a year with the planner", month_chart="Margin by month (€ thousand)",
        size_table="Battery size: what each strategy earns per year", col_batt="Battery", col_planner="Planner",
        col_adds="Planner adds", year_note="Today's contract: PPC pays the day-ahead price at every hour, no peak agreement. Margin after PPC fees, grid purchases, battery wear (€15/MWh discharged) and shortfall penalties. Battery cost covers the build only.",
        months=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        foot="Illustrative model, not a forecast of returns. Prices are modelled 15-minute curves scaled to Romania's publicly reported monthly day-ahead averages (OPCOM, via press); they are not exchange data. Minimum = 60% of the month's typical daily output, penalty €50/MWh unless changed, grid purchases don't count toward the minimum. Site: 30 MWp / 26 MW AC, southern Romania. Battery: 2-hour, 88% round trip. Tomorrow's weather: MET Norway Locationforecast (CC BY 4.0), converted to site output by the planner's cloud-layer model.",
        lang="Language",
    ),
    "tr": dict(
        title="Güneş + Batarya Planlayıcı",
        sub="26 MW güneş santrali · batarya seçeneği · günlük asgari teslimatlı, piyasa fiyatına bağlı PPC sözleşmesi",
        tab_day="Bir gün", tab_year="Tam bir yıl", scenario="Gün", battery="Batarya",
        none_today="Yok (bugün)", pays="PPC ödemesi", market="Piyasa fiyatı (bugün)", fixed="Sabit fiyat",
        fixed_price="Sabit PPC fiyatı (€/MWh)", peak="Pik anlaşması 17:00–22:00", peak_none="Yok (bugün)",
        peak_fixed="Sabit akşam fiyatı", peak_price="Akşam fiyatı (€/MWh)", avg="Yarının gün öncesi ortalaması (€/MWh)",
        minimum="PPC günlük asgari teslimat (MWh)", penalty="Eksik MWh başına ceza (€)",
        solo="Yalnızca güneş", rule="Basit batarya kuralı", planner="Planlayıcı ile", day="Gün",
        solo_d="Batarya yok: güneş varken sat", rule_d="11–15 arası şarj, 18–22 arası boşalt",
        needs="Batarya gerekir", vs_rule="basit kurala göre", sun="güneş tahmini",
        short="MWh asgarinin altında (ceza {p})", met="PPC asgarisi karşılandı",
        story_batt="Planlayıcı, güneş enerjisi ucuzken **{a:,.0f} MWh** depoluyor, satış fiyatından ucuz olduğu saatlerde şebekeden **{b:,.0f} MWh** alıyor ve fiyatların en yüksek olduğu saatlerde bataryadan **{c:,.0f} MWh** satıyor.",
        story_none="Batarya olmadan santral yalnızca güneş varken satış yapabilir.",
        wx="Santral için yarının hava tahmini", wx_src="MET Norway tahmini (CC BY 4.0), 9 Kasım 2026 07:16 UTC yayımı",
        hour="Saat", sky="Gökyüzü", low="Alçak bulut %", mid="Orta bulut %", high="Yüksek bulut %", temp="°C",
        wx_line="Tahmini üretim **{a:,.0f} MWh** (bulutsuz bir gün {b:,.0f} MWh verirdi) · bulutlu senaryo **{c:,.0f} MWh** · PPC asgarisi **{d:,.0f} MWh**",
        shortfall="PPC asgarisine göre açık bekleniyor.",
        ch_power="Planlayıcının her 15 dakikada yaptığı (MW; 0’ın altı = şarj)",
        ch_price="Piyasa fiyatı ve PPC ödemesi (€/MWh)", ch_soc="Batarya doluluğu (MWh)",
        c_solar="Güneş → PPC", c_batt="Batarya → PPC", c_sb="Güneş → batarya", c_gb="Şebeke → batarya", c_curt="Kısıtlanan",
        c_market="Gün öncesi piyasa (modellenmiş)", c_ppc="PPC ödemesi",
        level="Fiyat seviyesi", y2026="2026 bugüne kadar (ort. ~152 €)", y2025="2025 (ort. 108 €)", capex="Batarya maliyeti (MWh başına bin €)",
        a_year="yıllık", gwh="GWh güneş", payback="Batarya geri ödeme süresi", yrs="yıl", build="kurulum",
        per_year="planlayıcıyla yıllık kazanç", month_chart="Aylık marj (bin €)",
        size_table="Batarya boyutu: her stratejinin yıllık kazancı", col_batt="Batarya", col_planner="Planlayıcı",
        col_adds="Planlayıcı katkısı", year_note="Bugünkü sözleşme: PPC her saat gün öncesi fiyatı öder, pik anlaşması yok. Marj; PPC ücretleri, şebeke alımları, batarya aşınması (boşaltılan MWh başına 15 €) ve eksik teslimat cezaları düşülmüş haldedir. Batarya maliyeti yalnızca kurulumu kapsar.",
        months=["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
        foot="Örnek modeldir, getiri tahmini değildir. Fiyatlar, Romanya’nın kamuya açıklanan aylık gün öncesi ortalamalarına (OPCOM, basın aracılığıyla) ölçeklenmiş modellenmiş 15 dakikalık eğrilerdir; borsa verisi değildir. Asgari = ayın tipik günlük üretiminin %60’ı, değiştirilmedikçe ceza 50 €/MWh, şebeke alımları asgariye sayılmaz. Santral: 30 MWp / 26 MW AC, Güney Romanya. Batarya: 2 saatlik, %88 çevrim verimi. Yarının havası: MET Norway Locationforecast (CC BY 4.0), planlayıcının bulut katmanı modeliyle santral üretimine çevrildi.",
        lang="Dil",
    ),
}
SKY = {"en": dict(fog="Fog", cloudy="Cloudy", partlycloudy_day="Partly cloudy", partlycloudy_night="Partly cloudy",
                  fair_day="Fair", fair_night="Fair", clearsky_day="Clear", lightrain="Light rain", rain="Rain"),
       "tr": dict(fog="Sis", cloudy="Bulutlu", partlycloudy_day="Parçalı bulutlu", partlycloudy_night="Parçalı bulutlu",
                  fair_day="Az bulutlu", fair_night="Az bulutlu", clearsky_day="Açık", lightrain="Hafif yağmur", rain="Yağmur")}

lang = st.sidebar.radio("Language / Dil", ["tr", "en"], format_func=lambda x: "Türkçe" if x == "tr" else "English", horizontal=True)
L = T[lang]


def eur(v: float) -> str:
    s = f"{abs(v):,.0f}"
    s = s.replace(",", ".") + " €" if lang == "tr" else "€" + s
    return ("−" if v < 0 else "") + s


def eur_m(v: float) -> str:
    s = f"{abs(v) / 1e6:,.2f}"
    s = (s.replace(".", ",") + " milyon €") if lang == "tr" else ("€" + s + "M")
    return ("−" if v < 0 else "") + s


def eur_k(v: float) -> str:
    s = f"{abs(v) / 1e3:,.0f}"
    s = (s.replace(",", ".") + " bin €") if lang == "tr" else ("€" + s + "k")
    return ("−" if v < 0 else "") + s


def num(v: float, d: int = 0) -> str:
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "tr" else s


st.title(L["title"])
st.caption(L["sub"])
tab_day, tab_year = st.tabs([L["tab_day"], L["tab_year"]])

# ------------------------------------------------------------------ one day
with tab_day:
    keys = list(core.SCENARIOS)
    key = st.radio(L["scenario"], keys, horizontal=True,
                   format_func=lambda k: core.SCENARIOS[k][f"title_{lang}"])
    sc = core.SCENARIOS[key]
    st.caption(sc[f"blurb_{lang}"])

    c1, c2, c3 = st.columns(3)
    with c1:
        batt = st.radio(L["battery"], core.BATTERIES, horizontal=True,
                        format_func=lambda b: L["none_today"] if b == 0 else f"{b} MWh")
        if key == "live":
            day_avg = st.slider(L["avg"], 100, 500, 305, 5)
        else:
            day_avg = None
    with c2:
        pay_rule = st.radio(L["pays"], ["market", "fixed"], horizontal=True,
                            format_func=lambda r: L["market"] if r == "market" else L["fixed"])
        fixed_price = st.slider(L["fixed_price"], 40, 310, 305, 5, disabled=pay_rule == "market")
        peak = st.radio(L["peak"], [False, True], horizontal=True,
                        format_func=lambda p: L["peak_fixed"] if p else L["peak_none"])
        peak_price = st.slider(L["peak_price"], 100, 400, 305, 5, disabled=not peak)
    with c3:
        min_mwh = st.slider(L["minimum"], 0, 160, int(round(sc["min"])), 1, key=f"min_{key}")
        penalty = st.slider(L["penalty"], 0, 300, 50, 10)

    r = core.run_day(key, batt, pay_rule, fixed_price, peak, peak_price, min_mwh, penalty, day_avg)
    solo, rule, plan = r["solar_only"], r["simple_rule"], r["planner"]

    if batt:
        st.info(L["story_batt"].format(a=r["stored_mwh"], b=r["bought_mwh"], c=r["sold_from_battery_mwh"]))
    else:
        st.info(L["story_none"])

    if key == "live":
        st.subheader(L["wx"])
        st.caption(L["wx_src"])
        wx = pd.DataFrame([{L["hour"]: h["h"], L["sky"]: SKY[lang].get(h["sym"], h["sym"]),
                            L["low"]: round(h["low"]), L["mid"]: round(h["mid"]), L["high"]: round(h["high"]),
                            L["temp"]: round(h["temp"])} for h in sc["hours"]]).set_index(L["hour"])
        st.dataframe(wx.T.astype(str), use_container_width=True)
        clear_mwh = sum(sc["clear"]) * 0.25
        st.markdown(L["wx_line"].format(a=r["solar_mwh"], b=clear_mwh, c=r["solar_mwh"] * 0.7, d=r["min_mwh"]))
        if r["solar_mwh"] < r["min_mwh"]:
            st.warning(L["shortfall"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(L["solo"], eur(solo["margin"]), help=L["solo_d"])
    m2.metric(L["rule"], eur(rule["margin"]) if rule else "–", help=L["rule_d"] if rule else L["needs"])
    m3.metric(L["planner"], eur(plan["margin"]),
              delta=(eur(plan["margin"] - rule["margin"]) + " " + L["vs_rule"]) if rule else None)
    m4.metric(L["day"], f"{num(r['solar_mwh'])} MWh",
              help=f"{L['sun']} · {num(r['price_min'])}–{num(r['price_max'])} €/MWh")
    if plan["short"] > 0.05:
        st.warning(f"{num(plan['short'], 1)} " + L["short"].format(p=eur(plan["penalty"])))
    else:
        st.success(L["met"])

    tb = r["table"].set_index("time")
    st.subheader(L["ch_power"])
    st.bar_chart(tb[["solar_to_ppc_mw", "battery_to_ppc_mw", "solar_to_battery_mw", "grid_to_battery_mw", "curtailed_mw"]]
                 .rename(columns={"solar_to_ppc_mw": L["c_solar"], "battery_to_ppc_mw": L["c_batt"],
                                  "solar_to_battery_mw": L["c_sb"], "grid_to_battery_mw": L["c_gb"], "curtailed_mw": L["c_curt"]}),
                 color=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"], height=300)
    g1, g2 = st.columns([3, 2])
    with g1:
        st.subheader(L["ch_price"])
        st.line_chart(tb[["market_eur_mwh", "ppc_pays_eur_mwh"]].rename(
            columns={"market_eur_mwh": L["c_market"], "ppc_pays_eur_mwh": L["c_ppc"]}), color=["#2a78d6", "#eda100"], height=240)
    with g2:
        st.subheader(L["ch_soc"])
        if not batt:
            st.caption(L["needs"])
        else:
          st.area_chart(tb[["battery_mwh"]].rename(columns={"battery_mwh": L["ch_soc"]}), color=["#2a78d6"], height=240)

# ------------------------------------------------------------------ full year
with tab_year:
    y1, y2, y3 = st.columns(3)
    with y1:
        lvl = st.radio(L["level"], ["2026", "2025"], horizontal=True, format_func=lambda v: L["y" + v])
    with y2:
        ybatt = st.radio(L["battery"], core.BATTERIES, index=2, horizontal=True, key="ybatt",
                         format_func=lambda b: L["none_today"] if b == 0 else f"{b} MWh")
    with y3:
        capex = st.slider(L["capex"], 150, 350, 220, 10)

    base, Y = core.year(0, lvl), core.year(ybatt, lvl)
    solo_y, rule_y, plan_y, perf_y = (base["year"]["solar-only"], Y["year"]["simple rule"],
                                     Y["year"]["planner"], Y["year"]["perfect"])
    gain = plan_y - solo_y
    build = capex * 1000 * ybatt
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(L["solo"], eur_m(solo_y), help=f"{L['a_year']} · {num(base['solar'] / 1000, 1)} {L['gwh']}")
    k2.metric(L["rule"], eur_m(rule_y) if ybatt else "–")
    k3.metric(L["planner"], eur_m(plan_y),
              delta=(eur_k(plan_y - rule_y) + " " + L["vs_rule"]) if ybatt else None)
    k4.metric(L["payback"], f"{num(build / gain, 1)} {L['yrs']}" if ybatt and gain > 0 else "–",
              help=f"{eur_m(build)} {L['build']} · {eur_k(gain)} {L['per_year']}" if ybatt else None)

    months = sorted(Y["monthly"], key=int)
    mdf = pd.DataFrame({
        L["solo"]: [base["monthly"][m]["solar-only"] / 1000 for m in months],
        L["rule"]: [Y["monthly"][m]["simple rule"] / 1000 if ybatt else 0 for m in months],
        L["col_planner"]: [Y["monthly"][m]["planner"] / 1000 for m in months],
    }, index=pd.Index([f"{int(m):02d} {L['months'][int(m) - 1]}" for m in months]))
    st.subheader(L["month_chart"])
    st.bar_chart(mdf, stack=False, color=["#7a7972", "#eb6834", "#2a78d6"], height=320)

    st.subheader(L["size_table"])
    rows = []
    for b in core.BATTERIES:
        Z = core.year(b, lvl)
        rows.append({L["col_batt"]: L["none_today"] if b == 0 else f"{b} MWh",
                     L["rule"]: eur_m(Z["year"]["simple rule"]), L["col_planner"]: eur_m(Z["year"]["planner"]),
                     L["col_adds"]: ("+" + eur_k(Z["year"]["planner"] - Z["year"]["simple rule"])) if b else "–"})
    st.dataframe(pd.DataFrame(rows).set_index(L["col_batt"]), use_container_width=True)
    st.caption(L["year_note"])

st.divider()
st.caption(L["foot"])
