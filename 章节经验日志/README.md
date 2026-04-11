# 章节经验日志

> 存储每章创作的经验教训，供后续章节参考

---

## 日志格式

每个章节创建一个日志文件：`第N章_log.json`

```json
{
  "chapter": "第一章-天裂",
  "created_at": "2024-01-15",
  
  "techniques_used": [
    {"name": "有代价胜利", "effect": "有效", "note": "断臂作为代价"},
    {"name": "群体牺牲有姓名", "effect": "部分有效", "note": "需补充具体姓名"}
  ],
  
  "what_worked": [
    "断臂作为代价有冲击力",
    "开场氛围铺垫到位",
    "时间线清晰"
  ],
  
  "what_didnt_work": [
    "群体牺牲缺少具体姓名",
    "部分节奏过快"
  ],
  
  "insights": [
    {
      "content": "群体牺牲必须有具体姓名和动作，才能产生情感冲击",
      "scene_condition": "当描写群体牺牲场景时",
      "reusable": true
    }
  ],
  
  "for_next_chapter": [
    "配角牺牲必须有姓名和动作",
    "开场节奏可以更慢一些",
    "注意代价描写的具体化"
  ]
}
```

---

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `chapter` | string | 章节名称 |
| `created_at` | string | 创建时间 |
| `techniques_used` | array | 使用的技法及效果 |
| `what_worked` | array | 有效的做法 |
| `what_didnt_work` | array | 无效或有问题的做法 |
| `insights` | array | Evaluator提取的洞察 |
| `for_next_chapter` | array | 给下一章的建议 |

---

## 使用方式

创作第N章时，系统会自动：
1. 检索前3章的经验日志
2. 提取与当前场景相关的经验
3. 注入到作家的上下文中

---

*创建时间: 2024-01-01*