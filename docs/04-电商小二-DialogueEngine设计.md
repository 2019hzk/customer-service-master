# DialogueEngine 教材

## 第1章 对话处理流程

`DialogueEngine` 是一轮消息处理的调度中心。

它接收用户消息和 `DialogueState`，判断本轮走哪条处理路径，并返回机器人回复。

```mermaid
flowchart TD
    A[DialogueEngine.process] --> B[准备 Session]
    B --> C[创建 Turn]
    C --> D{消息类型?}
    
    D -->|文本消息| E[TurnPlanner]
    D -->|对象消息| F[写入 focused_object]
    
    E --> G[TurnPlanValidator]
    G --> H{本轮计划结果}
    
    H -->|知识问答| I[KnowledgeHandler]
    H -->|闲聊| J[ChitchatHandler]
    H -->|业务任务| K[TaskHandler]
    H -->|无效| L[ClarifyResponder]
    
    F --> M{是否匹配\n当前Task正在\n收集的槽位}
    M -->|匹配| K
    M -->|不匹配| L
    
    I & J & K & L --> N[提交本轮记录]
    N --> O[返回回复]
```

涉及组件如下：

| 组件 | 简要作用 |
| --- | --- |
| `DialogueState` | 保存会话、任务、聚焦对象和历史记录。 |
| `Turn` | 保存本轮用户输入和机器人输出。 |
| `TurnPlanner` | 根据文本消息和状态生成本轮计划。 |
| `TurnPlanValidator` | 检查本轮计划是否可靠、是否可执行。 |
| `ClarifyResponder` | 在计划不清晰时生成追问。 |
| `TaskHandler` | 处理业务任务。 |
| `KnowledgeHandler` | 处理知识问答。 |
| `ChitchatHandler` | 处理闲聊。 |

## 第2章 流程步骤细节

### 1. 准备会话

准备会话的核心问题只有一个：当前会话还能不能继续使用。

```mermaid
flowchart TD
    A[收到消息] --> B[读取当前 Session]
    B --> C{Session\n是否超时}
    C -->|未超时| D[继续当前 Session]
    C -->|超时| E[清理运行态]
    E --> F[创建新 Session]
    D --> G[会话准备完成]
    F --> G
```

如果会话超时，引擎会清理如下状态：

| 属性 | 处理 |
| --- | --- |
| `active_task` | 清空当前业务任务。 |
| `paused_tasks` | 清空暂停任务。 |
| `active_system_task` | 清空系统流程。 |
| `focused_object` | 清空当前关注对象。 |

### 2. 创建本轮记录

一条用户消息对应一轮对话，也就是一个 `Turn`。

```mermaid
flowchart LR
    A[用户消息] --> B[DialogueState.pending_turn]
    B --> C[机器人回复]
    C --> D[提交到当前 Session]
```

处理过程中，本轮记录暂存在 `DialogueState.pending_turn`。  
本轮结束后，再写入当前 `Session.turns`。

`Turn` 保存：

| 内容 | 说明 |
| --- | --- |
| 用户输入 | 本轮用户说了什么。 |
| 机器人输出 | 本轮系统回复了什么。 |

### 3. 判断消息类型

引擎先区分消息是文本，还是业务对象。

```mermaid
flowchart TD
    A[消息] --> B{消息类型}
    B -->|文本| C[进入文本理解]
    B -->|对象| D[进入对象处理]
```

| 类型 | 例子 | 处理重点 |
| --- | --- | --- |
| 文本 | “帮我查一下物流” | 理解用户想做什么。 |
| 对象 | 用户点击了某个订单 | 记录用户当前关注的对象。 |

### 4. 处理对象消息

对象消息通常来自前端点击，例如订单卡片、商品卡片。

引擎会先把对象写入 `DialogueState.focused_object`。

```mermaid
flowchart TD
    A[对象消息] --> B[写入 focused_object]
    B --> C{当前Task\n是否正需要\n这个对象}
    C -->|需要| D[继续Task]
    C -->|不需要| E[澄清用户意图]
```

例子：

| 用户操作 | 可能含义 |
| --- | --- |
| 点击订单 | 可能想查订单状态、查物流、申请退款。 |
| 点击商品 | 可能想看商品信息、问发货、问售后。 |

如果对象刚好能补齐当前任务需要的信息，就继续业务任务。  
如果只能知道“用户点了对象”，但不知道“想做什么”，就追问。

### 5. 处理文本消息

文本消息需要先交给 `TurnPlanner` 理解。

```mermaid
flowchart TD
    A[文本消息] --> B[读取 DialogueState]
    B --> C[TurnPlanner 生成本轮计划]
    C --> D[TurnPlanValidator 检查计划]
```

理解时会参考如下信息

| 信息 | 作用 |
| --- | --- |
| 最近对话 | 避免只看一句话造成误判。 |
| `active_task` | 判断用户是否在继续上一件事。 |
| `paused_tasks` | 判断用户是否想回到之前的事。 |
| `focused_object` | 利用订单或商品上下文。 |
| `flows` | 系统支持哪些业务流程，例如查订单、查物流、推荐商品。 |
| `knowledge_intents` | 系统支持哪些知识问答意图，例如商品信息、规则政策、常见问题。 |

`TurnPlanner` 不是凭空理解用户，而是在 `flows` 和 `knowledge_intents` 的能力范围内选择最合适的处理方向。

本轮计划可以先理解成一张“处理决策单”：

| 计划方向 | 具体内容 |
| --- | --- |
| 业务任务 | 启动/恢复/取消  哪个工作流 、设置哪个槽位 |
| 知识问答 | 问哪类知识问题 |
| 闲聊 | 用户不是办业务，也不是问知识，只需要自然回复。 |

一轮计划只能选择一个主要方向。方向不明确时，就不能直接执行。

### 6. 检查理解结果

`TurnPlanner` 的理解结果不能直接使用，需要由 `TurnPlanValidator` 检查。

```mermaid
flowchart TD
    A[本轮计划] --> B{是否通过校验}
    B -->|否| C[ClarifyResponder]
    B -->|是| D{处理方向}
    D -->|业务任务| E[TaskHandler]
    D -->|知识问答| F[KnowledgeHandler]
    D -->|闲聊| G[ChitchatHandler]
```

常见需要澄清的情况：

| 情况 | 例子 |
| --- | --- |
| 意图不明确 | “这个怎么办？” |
| 缺少对象 | “它卖多少钱？”，但没有商品。 |
| 多个方向冲突 | 同时像查订单，又像问售后政策。 |
| 系统无法确认 | 用户表达太短或上下文不足。 |

### 7. 澄清处理

当系统无法确定用户目的时，会交给 `ClarifyResponder` 追问。

```mermaid
flowchart LR
    A[无法确定] --> B[ClarifyResponder]
    B --> C[写入本轮回复]
    C --> D[返回给用户]
```

追问的目标是补齐关键信息。追问后，本轮不会继续执行业务处理。

### 8. 进入业务任务

当用户明确要办理业务时，引擎把本轮交给 `TaskHandler`。

```mermaid
flowchart LR
    A[业务任务方向] --> B[TaskHandler]
    B --> C[推进业务流程]
    C --> D[生成业务回复]
```

`TaskHandler` 会根据当前状态推进业务流程，并把回复写回本轮 `Turn`。  
例如查订单、查物流、推荐商品，都会走这条方向。

### 9. 进入知识问答

当用户是在问规则、政策、商品信息等问题时，引擎把本轮交给 `KnowledgeHandler`。

```mermaid
flowchart LR
    A[知识问答方向] --> B[暂停当前业务任务]
    B --> C[KnowledgeHandler]
    C --> D[生成知识回答]
```

知识问答会先暂停 `active_task`，再进入 `KnowledgeHandler`。  
这样用户临时问一个问题，不会破坏原来的业务流程。

### 10. 进入闲聊

当用户只是问候或简单聊天时，引擎把本轮交给 `ChitchatHandler`。

```mermaid
flowchart LR
    A[闲聊方向] --> B[暂停当前业务任务]
    B --> C[ChitchatHandler]
    C --> D[生成闲聊回复]
```

闲聊也会先暂停 `active_task`。它只生成闲聊回复，不推进业务流程。

### 11. 提交本轮记录

无论本轮是业务、知识、闲聊，还是追问，最后都要提交本轮记录。

```mermaid
flowchart TD
    A[pending_turn] --> B[写入 Session.turns]
    B --> C[清空 pending_turn]
    C --> D[返回 ProcessResult]
```

提交后，本轮就成为会话历史的一部分。返回结果包含：

| 内容 | 说明 |
| --- | --- |
| 用户 ID | 标识是谁的对话。 |
| 消息 ID | 标识是哪条消息的处理结果。 |
| 机器人回复 | 本轮要发给用户的消息。 |
