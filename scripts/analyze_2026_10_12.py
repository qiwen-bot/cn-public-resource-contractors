"""Read-only analysis of data/contractors.csv -> reports/analysis-2026-10-12.md"""
import csv, re, statistics, subprocess
from collections import Counter, defaultdict

rows = list(csv.DictReader(open('data/contractors.csv', encoding='utf-8')))
commit = subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()

# ---------- contractor normalization ----------
def norm(c):
    if '国泰新点' in c: return '国泰新点软件股份有限公司（含更名前江苏国泰新点）'
    return c
def group(c):
    if '中国移动' in c: return '中国移动（各分公司）'
    if '联通' in c or '中国联合网络' in c: return '中国联通（各分公司/子公司）'
    if '广州市中智软件' in c: return '广州市中智软件开发有限公司'
    return norm(c)
def telecom(c): return '移动/联通/电信合计' if re.search('中国移动|联通|中国联合网络|中国电信', c) else None

# ---------- amount parsing (万元) ----------
OVERRIDE = {  # (city, contractor-substring, year) -> (amount or None, reason)
 ('省本级','数字广东','2023'): (386.73+359.87, '两分项相加：软件开发386.73万+业务运营359.87万'),
 ('昌吉回族自治州','国泰新点','2026'): (419.4, '取notes所述合计约419.4万'),
 ('东莞市','东莞数字城市','2026#统筹'): (None, '2024万为市级政务信息化整包，交易中心分项未开放'),
 ('中山市','京信','2024'): (None, '4386万为政务信息化总包，含大量非交易中心内容'),
 ('省本级','长沙市中智','2023'): (None, '约83万为第三方检索汇总，非公告原文'),
 ('云浮市','中国移动','2026'): (936842.84/1e4, '第一中标候选人含税报价（非已确认成交价）'),
}
KW = r'(中标|成交|合同金额|合同|评审价|中标价|合计|金额)'
BAD = r'(预算|限价|上限|区间|以下|整包|总包)'
def parse_amount(r):
    key_city = r['city']
    for (city, sub, yr), v in OVERRIDE.items():
        y = yr.split('#')[0]
        tag = yr.split('#')[1] if '#' in yr else None
        if city == key_city and sub in r['contractor'] and y == r['contract_year'] and (tag is None or tag in r['system_name']):
            return v[0], 'override: '+v[1]
    t = r['notes']
    for m in re.finditer(r'(\d[\d,，]*(?:\.\d+)?)\s*(万元|万|元)', t):
        pre = t[max(0, m.start()-14):m.start()]
        if re.search(BAD, pre): continue
        if not re.search(KW, pre): continue
        num = float(m.group(1).replace(',', '').replace('，', ''))
        amt = num if m.group(2).startswith('万') else num/1e4
        return amt, 'regex'
    return None, 'none'

# ---------- type classification ----------
def classify(r):
    n = r['system_name']; t = n + ' ' + r['notes']
    if re.search(r'等保|密码应用|网络安全等级', n): return '等保/安全'
    if re.search(r'不见面|远程异地|CA|数字证书|评标仓|电子营业执照|机器管|AI|对接', n): return '专项子系统'
    if re.search(r'场地|设备采购', n): return '硬件/设施'
    om = re.search(r'运维|维护|运营|运行维护|维保|驻场', n)
    build = re.search(r'升级|改造|建设|开发|提升|整合|适配', n)
    if om and build: return '建设/升级+运维（混合）'
    if om: return '运维'
    if build: return '平台建设/升级'
    # generic names: fall back to notes
    if re.search(r'自建自运|法定', t): return '其他'
    if re.search(r'运维|维护', r['notes']) and not re.search(r'间接来源|论证意见列明', r['notes']): return '运维'
    if re.search(r'建设', r['notes']) and not re.search(r'间接来源|论证意见列明', r['notes']): return '平台建设/升级'
    return '其他'

def bucket(a):
    if a is None: return 'unknown'
    if a < 50: return '<50万'
    if a < 100: return '50–100万'
    if a <= 300: return '100–300万'
    return '>300万'
ORDER = ['<50万','50–100万','100–300万','>300万','unknown']

for r in rows:
    r['_amt'], r['_amt_src'] = parse_amount(r)
    r['_type'] = classify(r)
    r['_grp'] = group(r['contractor'])

GD = [r for r in rows if r['province']=='广东省']
YF = [r for r in rows if r['city']=='云浮市']
out = []
P = out.append
def tbl(head, data):
    P('| ' + ' | '.join(head) + ' |'); P('|' + '---|'*len(head))
    for d in data: P('| ' + ' | '.join(str(x) for x in d) + ' |')
    P('')
def fmt(a): return '—' if a is None else f'{a:,.2f}万'
def pct(a,b): return f'{a/b*100:.1f}%' if b else '—'

P('# 数据分析报告：cn-public-resource-contractors（2026-10-12）')
P('')
P(f'- 数据快照：`data/contractors.csv` @ commit `{commit[:7]}`（只读分析，未改动任何数据行）')
P(f'- 生成脚本：`scripts/analyze_2026_10_12.py`（可复现）')
P(f'- 行数：全表 **{len(rows)}**；广东 **{len(GD)}**；云浮 **{len(YF)}**')
P('')

# ---- assumptions check
yf_zz = sum('广州市中智软件' in r['contractor'] for r in YF)
yf_cm = sum('中国移动' in r['contractor'] for r in YF)
P('## 0. 用户假设核对')
P('')
tbl(['假设','数据实际','结论'], [
 ['全表 81 行', len(rows), '一致' if len(rows)==81 else '**不一致**'],
 ['云浮 4 行', len(YF), '一致' if len(YF)==4 else '**不一致**'],
 ['云浮 3 行中智', yf_zz, '一致' if yf_zz==3 else '**不一致**'],
 ['云浮 1 行中国移动', yf_cm, '一致' if yf_cm==1 else '**不一致**'],
])
P('补充说明（不算与假设冲突，但需注意）：')
P('- 移动那 1 行的采购人是**中国农业银行云浮分行**（招标编号 A44H660S26055002），不是云浮市公共资源交易中心；金额取自**中标候选人公示**里的报价，不是确认后的成交价。')
P('- CSV 的 `contract_year` 每行要么是一个年份，要么为空（空 %d 行，都是湖南间接来源）。CSV 里**没有** 2020/2023、2024–2026 这类区间值；区间只出现在项目名里（如“（2026-2027年）”），统计时不使用。' % sum(1 for r in rows if not r['contract_year']))
P('')

# ---- methodology
P('## 方法与口径')
P('')
P('**金额**：CSV 没有金额列。程序从 `notes` 里用正则提取第一个前面14字以内出现「中标/成交/合同/评审价/合计/金额」、且没有「预算/限价/上限/区间/以下/整包/总包」的 `数字+万元/元`，统一换算成万元。以下几行改用人工规则（见下表），其余行未取到金额则记为 unknown，**不做推测**。')
P('')
tbl(['行','处理','理由'], [[f"{c} / {s}", fmt(v[0]), v[1]] for (c,s,y),v in OVERRIDE.items()])
P('**项目类型**（规则依次判断，命中即停；先看 `system_name`，项目名太笼统时才看 `notes`）：')
P('1. 等保/安全：名称含 等保/密码应用/网络安全等级')
P('2. 专项子系统：名称含 不见面/远程异地/CA/数字证书/评标仓/电子营业执照/机器管/AI/对接')
P('3. 硬件/设施：名称含 场地/设备采购')
P('4. 名称同时含运维类词（运维/维护/运营/维保/驻场）和建设类词（升级/改造/建设/开发/提升/整合/适配）→ 建设/升级+运维（混合）；只含运维类词 → 运维；只含建设类词 → 平台建设/升级')
P('5. 项目名太笼统时看 notes；notes 写明「间接来源 / 论证意见列明」的湖南推定行、深圳法定机构自建自运行 → 其他')
P('')
P('**厂商归并**：')
P('- 国泰新点：「江苏国泰新点软件有限公司」是更名前的名称，与「国泰新点软件股份有限公司」合并统计。')
P('- 中智：**广州市中智软件开发有限公司（USCC 91440101731560976N）与长沙市中智信息技术开发有限公司（914301007072247105）按两家不同公司处理**。两者注册地和统一社会信用代码都不同，数据里也没有股权或集团关联的证据；简称相同不足以合并。“广州市中智软件”只是同一家公司的简称。')
P('- 运营商：中国移动、中国联通的各分公司分别列出，同时按集团汇总。')
P('')
P('**年份**：直接使用 `contract_year`；为空记为 unknown。')
P('')

# ---- 1 Yunfu
P('## 1. 云浮：全部行')
P('')
tbl(['项目','年份','承包商','采购人/口径','金额','类型'], [[
 r['system_name'], r['contract_year'], r['contractor'],
 '农行云浮分行' if '农行' in r['system_name'] else '云浮市公共资源交易中心',
 fmt(r['_amt']) + ('（候选人报价）' if '中国移动' in r['contractor'] else ''), r['_type']] for r in YF])
P(f'归属核对：广州中智 {yf_zz} 行，中国移动云浮分公司 {yf_cm} 行，合计 {len(YF)} 行，与用户假设一致。')
P('')

# ---- 2 whole dataset
def top(rs, keyf, k=10):
    return Counter(keyf(r) for r in rs).most_common(k)
P('## 2. 全表（全国）与广东')
P('')
P('### 2.1 承包商出现次数 Top10（按归并后名称）')
P('')
tbl(['#','承包商','全国','广东'], [[i+1, c, n, sum(1 for r in GD if r['_grp']==c)] for i,(c,n) in enumerate(top(rows, lambda r:r['_grp']))])
zz_gz = sum('广州市中智' in r['contractor'] for r in rows); zz_cs = sum('长沙市中智' in r['contractor'] for r in rows)
tel = [r for r in rows if telecom(r['contractor'])]
P('分组合计：')
P(f'- 广州中智：全国 {zz_gz} 行（广东 {sum("广州市中智" in r["contractor"] for r in GD)}）。长沙中智另计，全国 {zz_cs} 行（宁夏）。如果把两家合并成“中智”，就是 {zz_gz+zz_cs} 行，但本报告不采用这个口径。')
P(f'- 移动/联通/电信合计：{len(tel)} 行，分别为：' + '；'.join(f"{r['contractor']}（{r['city']} {r['contract_year']}）" for r in tel))
P('')

P('### 2.2 金额分布（只统计取到金额的行）')
P('')
def dist(rs):
    c = Counter(bucket(r['_amt']) for r in rs); return [c.get(b,0) for b in ORDER]
nat, gd, yf = dist(rows), dist(GD), dist(YF)
tbl(['区间']+ORDER, [['全国']+nat, ['广东']+gd, ['云浮']+yf])
pn = [r for r in rows if r['_amt'] is not None]
P(f'取到金额：全国 **{len(pn)}/{len(rows)}**（{pct(len(pn),len(rows))}），广东 {sum(1 for r in GD if r["_amt"] is not None)}/{len(GD)}，云浮 {sum(1 for r in YF if r["_amt"] is not None)}/{len(YF)}。注意：有些行的金额是多年合同总额或“/年”口径，例如株洲 131 万是两年合计，亳州 56 万是每年金额；这里按 notes 原文取值，不做年化。')
P('')

P('### 2.3 项目类型分布')
P('')
types = ['平台建设/升级','建设/升级+运维（混合）','运维','专项子系统','等保/安全','硬件/设施','其他']
tc = lambda rs: Counter(r['_type'] for r in rs)
a,b,c = tc(rows), tc(GD), tc(YF)
tbl(['类型','全国','广东','云浮'], [[t, a[t], b[t], c[t]] for t in types])

P('### 2.4 年度趋势（contract_year）')
P('')
yrs = sorted({r['contract_year'] or 'unknown' for r in rows}, key=lambda x:(x=='unknown',x))
tbl(['年份','全国行数','广东行数','全国取到金额行数','全国金额合计(万)'], [[y,
  sum(1 for r in rows if (r['contract_year'] or 'unknown')==y),
  sum(1 for r in GD if (r['contract_year'] or 'unknown')==y),
  sum(1 for r in rows if (r['contract_year'] or 'unknown')==y and r['_amt'] is not None),
  f"{sum(r['_amt'] for r in rows if (r['contract_year'] or 'unknown')==y and r['_amt'] is not None):,.1f}"] for y in yrs])
P('说明：2026 年行数最多，主要因为本轮集中采集了近期公告（采集偏差），不能直接看成市场在增长。')
P('')

# ---- 3 YF vs GD
def conc(rs):
    c = Counter(r['_grp'] for r in rs).most_common()
    t2 = sum(n for _,n in c[:2]); return c[:2], t2, len(rs)
def mean(rs):
    v=[r['_amt'] for r in rs if r['_amt'] is not None]
    return (statistics.mean(v), statistics.median(v), len(v)) if v else (None,None,0)
PLAT = {'平台建设/升级','建设/升级+运维（混合）'}
P('## 3. 云浮 vs 广东（同时给出全国）')
P('')
rowsout=[]
for name, rs in [('云浮',YF),('广东',GD),('全国',rows)]:
    (t,s,n)=conc(rs); m,md,k=mean(rs)
    pl=sum(1 for r in rs if r['_type'] in PLAT)
    rowsout.append([name, n, '；'.join(f'{x}×{y}' for x,y in t), pct(s,n), fmt(m), fmt(md), k, f'{pl}/{n} = {pct(pl,n)}'])
tbl(['范围','n','前两名供应商','前两名份额','平均金额','中位数','金额n','平台建设/升级占比*'], rowsout)
P('\\* 平台建设/升级占比 = 类型为「平台建设/升级」或「建设/升级+运维（混合）」的行数 ÷ 总行数。')
m_yf=mean(YF)[0]; m_gd=mean(GD)[0]
yf_ex=[r for r in YF if '中国移动' not in r['contractor']]
P(f'- 集中度：云浮前两名份额 100%（行数只有 4，前两名天然就覆盖全部，这个指标在云浮几乎没有区分度）。只看第一名：中智 3/4 = 75%；广东第一名份额见上表。')
P(f'- 平均金额：云浮 {fmt(m_yf)}（n={mean(YF)[2]}），广东 {fmt(m_gd)}（n={mean(GD)[2]}），云浮**{"更低" if m_yf<m_gd else "更高"}**。如果剔除移动候选人报价那一行，云浮为 {fmt(mean(yf_ex)[0])}（n={mean(yf_ex)[2]}）。')
P('- 小样本警告：云浮只有 4 行，任何比例、均值都对单行非常敏感，换一行结论就可能反过来。广东 29 行也不算多；而且数据是人工采集的，不是全部公告，这些比较只能作为线索参考，不能下统计结论。')
P('')

# ---- 4 conclusions
P('## 4. 结论')
P('')
P('1. **在交易中心这个采购人下，中智占主导**：交易中心作为采购人的 3 行全部是广州中智，覆盖 2023 年不见面开标/远程异地评标建设、2026 年平台优化升级（46.2 万）、2026–2027 年运维（67 万）。')
P('2. **移动“进入”的证据弱**：唯一一行移动记录的采购人是农行云浮分行，金额是候选人报价。从内容看（农行系统对接、门禁、电子签名等），更像是银行出资配套的升级，不能说明移动进入了交易中心核心系统的承建/运维。是否最终签约，还要找结果公告或合同公告确认。')
P('3. **同一厂商通过单一来源同时拿下升级和运维**：2026 年中智通过两次单一来源分别获得升级（YFCG126D08008）和运维（YFCG126D0700601），运维范围还包括它在 2023 年建设的不见面开标/远程异地评标系统。这符合“原厂商锁定”的特征。**但要说明**：这两则云浮单一来源**结果公告**正文和 PDF 附件里都**没有写**单一来源的理由（例如“原承建方”）；本轮也没有找到对应的单一来源征求意见公示。所以“因为是原承建方”是推断，不是公告原文。数据集中能直接引用原承建方/源代码理由的单一来源例子在其他地区：岳阳 2019（论证意见写明由该公司承建）、衡阳 2020、株洲 2021（拥有源代码）、郑州 2026（2017 年起开发并持续运维）、上饶 2025（省平台软件供应商）、福建 2023（指定广联达）。')
P('4. **覆盖偏差**：数据集是按需人工采集的，并不完整。2026 年和广东的公告被重点采集；国泰新点在湘赣皖等地出现很多，部分原因是公开公告更容易找到。湖南有 4 行是间接推定的（没有年份），金额只取到 %d/%d 行。不能把这里的行数份额当成市场份额。' % (len(pn), len(rows)))
P('')
open('reports/analysis-2026-10-12.md','w',encoding='utf-8').write('\n'.join(out))
# debug dump
#for r in rows: print(r['city'][:5], r['contract_year'], r['contractor'][:12], fmt(r['_amt']), r['_amt_src'][:10], r['_type'])
