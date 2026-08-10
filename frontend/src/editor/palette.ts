// 四种节点 + 开始节点的视觉元数据（克制配色：彩色只用于表达类型）
export const NODE_META: Record<string, { label: string; color: string; bg: string }> = {
  llm: { label: '对话生成', color: '#1677ff', bg: '#e6f4ff' },
  decision: { label: '判断分支', color: '#fa8c16', bg: '#fff7e6' },
  http: { label: '获取数据', color: '#52c41a', bg: '#f6ffed' },
  end: { label: '结束', color: '#8c8c8c', bg: '#fafafa' },
  start: { label: '开始', color: '#333', bg: '#fff' },
}

// 可拖入的节点类型（不含 start / end 从节点库拖入？end 允许）
export const PALETTE: { type: string; label: string }[] = [
  { type: 'llm', label: '对话生成' },
  { type: 'decision', label: '判断分支' },
  { type: 'http', label: '获取数据' },
  { type: 'end', label: '结束' },
]
