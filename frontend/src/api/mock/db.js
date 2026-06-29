// Mock 假数据：结构即未来后端 API 的数据契约。

export const contracts = [
  { id: 'c1', name: '智慧园区软件采购合同', partyA: '华城数字建设有限公司', partyB: '云启科技有限公司', type: '采购合同', risk: '高风险', riskCount: 3, riskLevel: 'red', updatedAt: '今天 10:20' },
  { id: 'c2', name: '年度技术服务框架协议', partyA: '远航实业集团', partyB: '新程信息技术有限公司', type: '服务合同', risk: '中风险', riskCount: 5, riskLevel: 'amber', updatedAt: '今天 09:24' },
  { id: 'c3', name: '办公场地租赁合同', partyA: '智创产业发展有限公司', partyB: '城发置业有限公司', type: '租赁合同', risk: '低风险', riskCount: 0, riskLevel: 'green', updatedAt: '昨天 16:12' },
  { id: 'c4', name: '品牌联合营销协议', partyA: '华城数字建设有限公司', partyB: '星河传媒有限公司', type: '合作协议', risk: '中风险', riskCount: 2, riskLevel: 'amber', updatedAt: '06-17' },
  { id: 'c5', name: '设备维保服务合同', partyA: '启明制造有限公司', partyB: '恒远技术服务有限公司', type: '服务合同', risk: '低风险', riskCount: 0, riskLevel: 'green', updatedAt: '06-16' },
]

// 审核维度
export const dimensions = ['基础核查', '法务风险', '财务风险', '形式核查']

// 风险后果类别（审核点卡片副标题）
export const riskCategories = ['权利义务失衡', '履约保障不足', '合规与权属风险']

// 审核点：name + category(后果类别，卡片副标题) + dimension(所属维度) + 默认勾选
export const points = [
  { id: 'p1', name: '主体信息与签署授权', category: '合规与权属风险', dimension: '基础核查', desc: '核查甲乙方名称、统一社会信用代码、法定代表人与授权是否完整一致', riskPoints: 2, status: '已启用', defaultChecked: true, updatedAt: '06-18' },
  { id: 'p2', name: '标的范围与服务边界', category: '权利义务失衡', dimension: '基础核查', desc: '标的、服务范围与交付物边界是否清晰', riskPoints: 1, status: '已启用', defaultChecked: true, updatedAt: '06-18' },
  { id: 'p3', name: '价格、发票与付款条件', category: '权利义务失衡', dimension: '财务风险', desc: '价格、付款节点、比例与发票约定是否对我方不利', riskPoints: 3, status: '已启用', defaultChecked: true, updatedAt: '06-18' },
  { id: 'p4', name: '交付计划与验收机制', category: '履约保障不足', dimension: '法务风险', desc: '识别默示验收等对我方不利的验收条款', riskPoints: 2, status: '已启用', defaultChecked: true, updatedAt: '06-17' },
  { id: 'p5', name: '质量保证与售后服务', category: '履约保障不足', dimension: '法务风险', desc: '质保期、响应时限与售后责任是否明确', riskPoints: 1, status: '已启用', defaultChecked: true, updatedAt: '06-17' },
  { id: 'p6', name: '知识产权与成果归属', category: '合规与权属风险', dimension: '法务风险', desc: '成果、数据与衍生知识产权归属是否清晰', riskPoints: 2, status: '已启用', defaultChecked: true, updatedAt: '06-16' },
  { id: 'p7', name: '数据安全与保密义务', category: '合规与权属风险', dimension: '法务风险', desc: '数据安全、保密范围与期限是否完备', riskPoints: 1, status: '已启用', defaultChecked: true, updatedAt: '06-16' },
  { id: 'p8', name: '违约责任与赔偿上限', category: '履约保障不足', dimension: '法务风险', desc: '违约金比例、赔偿上限是否足以覆盖损失', riskPoints: 3, status: '已启用', defaultChecked: true, updatedAt: '06-15' },
  { id: 'p9', name: '合同解除与退出机制', category: '权利义务失衡', dimension: '法务风险', desc: '解除条件、退出与善后安排是否对等', riskPoints: 1, status: '已启用', updatedAt: '06-15' },
  { id: 'p10', name: '法律适用与争议解决', category: '权利义务失衡', dimension: '法务风险', desc: '管辖、仲裁与法律适用是否对我方有利', riskPoints: 1, status: '已启用', updatedAt: '06-14' },
  { id: 'p11', name: '需求变更与费用调整', category: '履约保障不足', dimension: '财务风险', desc: '变更流程与相应费用调整机制是否清晰', riskPoints: 1, status: '已启用', updatedAt: '06-14' },
  { id: 'p12', name: '附件完整性与签章形式', category: '合规与权属风险', dimension: '形式核查', desc: '附件、签字盖章、份数与生效条件是否完整', riskPoints: 1, status: '已启用', updatedAt: '06-13' },
  { id: 'p13', name: '发票与费用承担', category: '权利义务失衡', dimension: '财务风险', desc: '税费、发票类型与开具时点约定是否明确', riskPoints: 1, status: '已启用', updatedAt: '06-13' },
  { id: 'p14', name: '不可抗力处理', category: '履约保障不足', dimension: '法务风险', desc: '不可抗力情形、通知与责任免除是否合理', riskPoints: 1, status: '已启用', updatedAt: '06-12' },
  { id: 'p15', name: '转包与分包限制', category: '合规与权属风险', dimension: '法务风险', desc: '是否限制擅自转包、分包及相应责任', riskPoints: 1, status: '已启用', updatedAt: '06-12' },
  { id: 'p16', name: '保密期限与范围', category: '合规与权属风险', dimension: '法务风险', desc: '保密信息范围、期限与例外是否清晰', riskPoints: 1, status: '已启用', updatedAt: '06-11' },
  { id: 'p17', name: '结算与对账方式', category: '履约保障不足', dimension: '财务风险', desc: '结算周期、对账确认与争议处理是否明确', riskPoints: 1, status: '已启用', updatedAt: '06-11' },
  { id: 'p18', name: '通知与送达条款', category: '权利义务失衡', dimension: '形式核查', desc: '通知方式、送达地址与生效时点是否完备', riskPoints: 1, status: '已停用', updatedAt: '06-10' },
]

// 合同类型
export const contractTypes = [
  { id: 't1', code: 'PURCHASE', name: '采购合同', stance: '甲方立场', desc: '以购买货物、设备或软件产品为主要目的', keywords: '采购,供货,验收', relatedPoints: 3, status: '已启用', updatedAt: '06-18' },
  { id: 't2', code: 'SERVICE', name: '服务合同', stance: '甲方立场', desc: '以服务交付、成果验收为主要目的', keywords: '服务,技术支持,维保', relatedPoints: 3, status: '已启用', updatedAt: '06-17' },
  { id: 't3', code: 'SALE', name: '销售合同', stance: '乙方立场', desc: '我方向客户销售产品或软件', keywords: '销售,供货,回款', relatedPoints: 3, status: '已启用', updatedAt: '06-16' },
  { id: 't4', code: 'LEASE', name: '租赁合同', stance: '甲方立场', desc: '涉及场地、设备或资产租赁', keywords: '租赁,租金,押金', relatedPoints: 3, status: '已启用', updatedAt: '06-15' },
  { id: 't5', code: 'COOP', name: '合作协议', stance: '乙方立场', desc: '双方共同投入资源并约定权责', keywords: '合作,共建,分成', relatedPoints: 3, status: '已启用', updatedAt: '06-14' },
  { id: 't6', code: 'SUPP', name: '补充协议', stance: '甲方立场', desc: '针对既有合同进行补充约定', keywords: '补充,变更,附件', relatedPoints: 3, status: '已停用', updatedAt: '06-13' },
]

// 审核维度（管理表）
export const dimensionDetail = [
  { id: 'd1', name: '基础核查', desc: '主体信息、资质及基本合规要素', status: '已启用', updatedAt: '06-19' },
  { id: 'd2', name: '财务检查', desc: '付款、发票、违约金等财务相关条款', status: '已启用', updatedAt: '06-18' },
  { id: 'd3', name: '一致性检查', desc: '知识产权、数据权属及条款一致性', status: '已启用', updatedAt: '06-17' },
  { id: 'd4', name: '法务风险', desc: '违约责任、解除权、争议解决', status: '已启用', updatedAt: '06-16' },
  { id: 'd5', name: '形式核查', desc: '附件完整性、签章页核验', status: '已停用', updatedAt: '06-15' },
]

// 选择审核维度页的可选维度
export const selectableDimensions = [
  { name: '基础核查', desc: '主体信息、签约授权、基础要素完整性。' },
  { name: '法务风险', desc: '权利义务、违约责任、解除与争议解决。' },
  { name: '财务风险', desc: '付款、发票、税务、结算及费用承担。' },
  { name: '形式核查', desc: '签章、附件、文本格式和材料完整性。' },
]

// 风险分级规则
export const riskRules = [
  { id: 'r1', name: '商业合理性风险', desc: '识别价格、周期、责任是否明显偏离商业惯例', high: '关键商业条件严重失衡，可能造成重大损失', low: '存在轻微不对等但可控', status: '已启用' },
  { id: 'r2', name: '合规风险', desc: '是否违反法律法规强制性规定', high: '违反强制性规定，条款可能无效', low: '表述不严谨但不违法', status: '已启用' },
]

// 审核结果（按合同 id）：左栏原文 + 右栏风险点（按维度 Tab + 高/低风险筛选）
export function buildAuditResult(contractId) {
  const target = contracts.find((c) => c.id === contractId) || contracts[0]
  return {
    contractId: target.id,
    contractName: target.name,
    partyA: target.partyA,
    partyB: target.partyB,
    docType: 'Word',
    // 左栏原文（演示，highlight 为命中风险的条款）
    originalText: [
      { type: 'h2', text: target.name },
      { type: 'p', text: `甲方：${target.partyA}` },
      { type: 'p', text: `乙方：${target.partyB}` },
      { type: 'h3', text: '第四条 项目交付与验收' },
      { type: 'p', text: '乙方应于合同签订后 60 个工作日内完成系统部署。' },
      { type: 'highlight', text: '若甲方在十个工作日内未提出书面异议，则视为项目自动验收通过。' },
      { type: 'h3', text: '第七条 违约责任' },
      { type: 'highlight', text: '乙方逾期交付的，每日按合同总金额的 0.03% 支付违约金，累计上限为 3%。' },
      { type: 'h3', text: '第九条 数据与知识产权' },
      { type: 'highlight', text: '项目形成的数据及衍生成果由双方共同所有。' },
    ],
    // 维度 Tab 顺序
    dimensions: ['基础核查', '法务风险', '财务风险', '形式核查'],
    // 风险点列表（level: major 重大风险 / general 一般风险）
    // 卡片字段：desc 风险说明 / analysis 风险分析 / example 修改示例 / clause 所属条款（用于定位原文）
    risks: [
      {
        dimension: '基础核查',
        title: '主体信息缺失风险',
        level: 'major',
        desc: '合同主体信息缺失。甲方信息不完整，名称、地址、法定代表人、联系方式和统一社会信用代码缺失；乙方信息同样不完整。',
        analysis:
          '主体信息不完整将导致责任主体难以确认，一旦发生争议，可能因签约主体不明而影响合同效力与追责，建议补全双方主体信息后再行签署。',
        example:
          '甲方名称：XXX公司　地址：XXX市XXX区XXX路XXX号　法定代表人：XXX　电话：XXX　统一社会信用代码：XXX。\n乙方信息同上补全，并明确责任主体、履行条件和确认方式。',
        clause: '主体信息条款',
      },
      {
        dimension: '基础核查',
        title: '法定代表人授权证明缺失',
        level: 'major',
        desc: '未见法定代表人身份证明或授权委托书，签署主体的签约权限无法确认。',
        analysis: '若签署人无相应授权，合同可能被认定为效力待定或无效，给我方带来履约与追责障碍。',
        example: '补充法定代表人身份证明或加盖公章的授权委托书，明确签署人权限范围与有效期。',
        clause: '签署授权条款',
      },
      {
        dimension: '法务风险',
        title: '默示验收风险',
        level: 'major',
        desc: '存在"逾期未提书面异议即视为自动验收通过"的默示验收条款。',
        analysis: '默示验收可能导致尚未发现的质量问题被默认接受，使我方丧失提出整改或索赔的权利。',
        example: '删除自动验收表述，改为双方签署书面验收单后方视为验收完成，并约定明确的验收标准。',
        clause: '第四条 项目交付与验收',
      },
      {
        dimension: '法务风险',
        title: '违约责任失衡',
        level: 'major',
        desc: '违约金累计上限仅为合同总金额的 3%，可能不足以覆盖逾期造成的实际损失。',
        analysis: '过低的违约金上限会削弱违约约束力，一旦对方违约，我方实际损失可能远高于可主张的违约金。',
        example: '提高违约金上限或改为按日累计且不设过低封顶，并补充守约方在重大违约时的合同解除权。',
        clause: '第七条 违约责任',
      },
      {
        dimension: '法务风险',
        title: '知识产权归属不清',
        level: 'general',
        desc: '"数据及衍生成果由双方共同所有"表述笼统，易引发后续使用与授权争议。',
        analysis: '共有而无使用边界、授权范围及商业化约定，后续任一方主张权利都可能受限或产生纠纷。',
        example: '明确各类成果、数据与衍生知识产权的归属、许可范围与使用限制，并约定商业化收益分配。',
        clause: '第九条 数据与知识产权',
      },
      {
        dimension: '财务风险',
        title: '付款节点资金风险',
        level: 'major',
        desc: '验收后尾款比例较高且无明确支付时限，存在资金占用与回款风险。',
        analysis: '尾款比例高且缺少支付时限约束，可能造成长期资金占用，影响我方现金流。',
        example: '明确尾款支付时限，适当下调验收尾款比例，并约定逾期付款的利息或违约金。',
        clause: '第五条 付款方式',
      },
      {
        dimension: '财务风险',
        title: '发票与税费约定缺失',
        level: 'general',
        desc: '未约定发票类型、税率与开具时点，可能影响税务处理与抵扣。',
        analysis: '缺少发票与税费约定，可能导致无法及时取得合规发票，影响成本列支与进项抵扣。',
        example: '补充发票类型（增值税专用发票）、税率与"先票后款"等开具与付款顺序约定。',
        clause: '发票与费用承担条款',
      },
      {
        dimension: '形式核查',
        title: '签章形式不完整',
        level: 'general',
        desc: '合同份数、骑缝章与附件清单约定不完整，可能影响合同完整性认定。',
        analysis: '签章与附件形式不规范，可能在争议时被质疑文本完整性或附件效力。',
        example: '补充合同份数、骑缝章要求与附件清单，明确各附件与正文的效力关系。',
        clause: '附件完整性与签章形式条款',
      },
    ],
  }
}

export const profile = {
  name: '伊路',
  account: 'yilu@company.com',
  company: '华城数字建设有限公司',
  role: '企业管理员',
  phone: '138****6688',
  email: 'yilu@company.com',
}
