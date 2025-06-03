# ChatGPT-on-WeChat 技术架构图

## 系统架构图

```mermaid
graph TB
    subgraph "用户层"
        U1[微信用户]
        U2[企业微信用户]
        U3[钉钉用户]
        U4[Web用户]
    end

    subgraph "外部平台"
        WX[微信服务器]
        WXCOM[企业微信服务器]
        DD[钉钉服务器]
        WEB[浏览器]
    end

    subgraph "应用层 (App Layer)"
        APP[app.py<br/>程序入口<br/>生命周期管理]
        CONFIG[config.py<br/>配置管理<br/>参数加载]
    end

    subgraph "通道层 (Channel Layer)"
        CF[channel_factory.py<br/>通道工厂]

        subgraph "具体通道实现"
            WMP[WechatMPChannel<br/>微信公众号通道]
            WMPC[WechatComAppChannel<br/>企业微信应用通道]
            DTC[DingTalkChannel<br/>钉钉通道]
            WC[WebChannel<br/>Web通道]
        end

        CC[ChatChannel<br/>聊天通道基类<br/>消息处理核心逻辑]
        CH[Channel<br/>通道抽象基类]
    end

    subgraph "桥接层 (Bridge Layer)"
        BR[Bridge<br/>业务逻辑桥接<br/>统一API接口]
        CTX[Context<br/>消息上下文]
        RPL[Reply<br/>回复对象]
    end

    subgraph "插件层 (Plugin Layer)"
        PM[PluginManager<br/>插件管理器<br/>事件分发]

        subgraph "核心插件"
            P1[Hello<br/>示例插件]
            P2[Banwords<br/>敏感词过滤]
            P3[Tool<br/>工具调用]
            P4[LinkAI<br/>LinkAI集成]
        end

        PE[Plugin Event System<br/>事件系统]
    end

    subgraph "机器人层 (Bot Layer)"
        BF[bot_factory.py<br/>机器人工厂]

        subgraph "AI模型实现"
            GPT[ChatGPTBot<br/>OpenAI GPT]
            BAIDU[BaiduWenxinBot<br/>百度文心]
            CLAUDE[ClaudeAPIBot<br/>Claude]
            ZHIPU[ZHIPUAIBot<br/>智谱AI]
            ALI[AliQwenBot<br/>阿里通义千问]
        end

        BOT[Bot<br/>机器人抽象基类]
        SM[SessionManager<br/>会话管理]
    end

    subgraph "工具层 (Utility Layer)"
        subgraph "语音处理"
            V2T[Voice to Text<br/>语音转文字]
            T2V[Text to Voice<br/>文字转语音]
        end

        subgraph "翻译服务"
            TRANS[Translator<br/>翻译器]
        end

        subgraph "基础服务"
            LOG[Logger<br/>日志系统]
            UTIL[Utils<br/>工具函数]
            CACHE[Cache<br/>缓存系统]
        end
    end

    subgraph "外部服务"
        OPENAI[OpenAI API]
        AZURE[Azure Speech]
        VOLC[VolcEngine API<br/>豆包模型]
        BAIDU_API[百度API]
        LINKAI_API[LinkAI API]
    end

    %% 用户交互流
    U1 --> WX
    U2 --> WXCOM
    U3 --> DD
    U4 --> WEB

    %% 平台到通道
    WX --> WMP
    WXCOM --> WMPC
    DD --> DTC
    WEB --> WC

    %% 应用层连接
    APP --> CONFIG
    APP --> CF

    %% 通道层连接
    CF --> WMP
    CF --> WMPC
    CF --> DTC
    CF --> WC

    WMP --> CC
    WMPC --> CC
    DTC --> CC
    WC --> CC

    CC --> CH

    %% 核心处理流
    CC --> CTX
    CTX --> PM
    PM --> PE
    PE --> P1
    PE --> P2
    PE --> P3
    PE --> P4

    CC --> BR
    BR --> BF
    BF --> GPT
    BF --> BAIDU
    BF --> CLAUDE
    BF --> ZHIPU
    BF --> ALI

    GPT --> BOT
    BAIDU --> BOT
    CLAUDE --> BOT
    ZHIPU --> BOT
    ALI --> BOT

    BOT --> SM
    BR --> RPL

    %% 工具层连接
    BR --> V2T
    BR --> T2V
    BR --> TRANS

    CC --> LOG
    CC --> UTIL
    CC --> CACHE

    %% 外部服务连接
    GPT -.-> OPENAI
    V2T -.-> AZURE
    T2V -.-> AZURE
    BAIDU -.-> BAIDU_API
    GPT -.-> VOLC
    P4 -.-> LINKAI_API

    %% 样式定义
    classDef userLayer fill:#e1f5fe
    classDef appLayer fill:#f3e5f5
    classDef channelLayer fill:#e8f5e8
    classDef bridgeLayer fill:#fff3e0
    classDef pluginLayer fill:#fce4ec
    classDef botLayer fill:#e0f2f1
    classDef utilLayer fill:#f1f8e9
    classDef externalLayer fill:#ffebee

    class U1,U2,U3,U4 userLayer
    class APP,CONFIG appLayer
    class CF,WMP,WMPC,DTC,WC,CC,CH channelLayer
    class BR,CTX,RPL bridgeLayer
    class PM,P1,P2,P3,P4,PE pluginLayer
    class BF,GPT,BAIDU,CLAUDE,ZHIPU,ALI,BOT,SM botLayer
    class V2T,T2V,TRANS,LOG,UTIL,CACHE utilLayer
    class OPENAI,AZURE,VOLC,BAIDU_API,LINKAI_API externalLayer
```

## 消息处理流程图

```mermaid
sequenceDiagram
    participant User as 用户
    participant WeChat as 微信服务器
    participant Channel as WechatMPChannel
    participant Queue as 消息队列
    participant Plugin as PluginManager
    participant Bridge as Bridge
    participant Bot as AI Bot
    participant External as 外部API

    %% 消息接收阶段
    User->>WeChat: 发送消息
    WeChat->>Channel: POST /callback
    Channel->>Channel: 解析消息
    Note over Channel: parse_message()
    Channel->>Channel: 创建Context
    Note over Channel: _compose_context()

    %% 插件预处理
    Channel->>Plugin: ON_RECEIVE_MESSAGE
    Plugin->>Plugin: 事件处理
    Plugin-->>Channel: 处理结果

    %% 异步处理
    Channel->>Queue: 消息入队
    Note over Queue: produce()
    Queue->>Channel: 异步处理
    Note over Channel: _handle()

    %% 插件处理链
    Channel->>Plugin: ON_HANDLE_CONTEXT
    Plugin->>Plugin: 插件链处理
    Note over Plugin: 按优先级依次处理
    Plugin-->>Channel: 修改Context/Reply

    %% AI处理
    Channel->>Bridge: 生成回复
    Note over Bridge: _generate_reply()
    Bridge->>Bot: 调用AI模型
    Note over Bot: reply()
    Bot->>External: API调用
    External-->>Bot: 返回结果
    Bot-->>Bridge: Reply对象
    Bridge-->>Channel: 处理结果

    %% 回复装饰
    Channel->>Plugin: ON_DECORATE_REPLY
    Plugin->>Plugin: 装饰回复
    Plugin-->>Channel: 装饰结果

    %% 发送回复
    Channel->>Plugin: ON_SEND_REPLY
    Plugin-->>Channel: 发送前处理
    Channel->>WeChat: 发送回复
    Note over Channel: send()
    WeChat->>User: 推送回复

    %% 异常处理
    Note over Channel,External: 各阶段都有异常处理和重试机制
```

## 当前配置下的执行路径

```mermaid
graph LR
    subgraph "当前配置路径"
        START[系统启动] --> LOAD[加载config.json]
        LOAD --> |channel_type=wechatmp| WMP[创建WechatMPChannel]
        WMP --> |port=18082| LISTEN[监听微信回调]

        LISTEN --> MSG[接收消息]
        MSG --> PARSE[解析微信消息]
        PARSE --> CTX[创建Context]

        CTX --> PLUGIN[插件处理]
        PLUGIN --> |model=ep-20240629044418-hpqwb| VOLC[调用豆包API]
        VOLC --> |api_base=ark.cn-beijing.volces.com| RESPONSE[获取AI回复]

        RESPONSE --> |speech_recognition=true| VOICE[语音处理]
        VOICE --> |voice_to_text=azure| AZURE_STT[Azure语音识别]
        VOICE --> |text_to_voice=azure| AZURE_TTS[Azure语音合成]

        RESPONSE --> DECORATE[装饰回复]
        DECORATE --> SEND[发送回复]
        SEND --> WX[推送给用户]
    end

    subgraph "配置项影响"
        CONFIG[config.json] --> |决定通道类型| CHANNEL_TYPE[channel_type: wechatmp]
        CONFIG --> |决定AI模型| MODEL[model: ep-20240629044418-hpqwb]
        CONFIG --> |决定监听端口| PORT[wechatmp_port: 18082]
        CONFIG --> |决定语音服务| VOICE_CONFIG[voice_to_text/text_to_voice: azure]
        CONFIG --> |控制调试输出| DEBUG[debug: true]
    end
```

## 核心组件关系图

```mermaid
classDiagram
    class Channel {
        <<abstract>>
        +startup()
        +send(reply, context)
    }

    class ChatChannel {
        +_compose_context()
        +_handle()
        +_generate_reply()
        +_decorate_reply()
        +_send_reply()
        +produce()
        +consume()
    }

    class WechatMPChannel {
        +client: WechatMPClient
        +crypto: WeChatCrypto
        +startup()
        +send()
    }

    class Bridge {
        +fetch_reply_content()
        +fetch_voice_to_text()
        +fetch_text_to_voice()
        +get_bot()
    }

    class Bot {
        <<abstract>>
        +reply(query, context)
    }

    class ChatGPTBot {
        +reply()
        +reply_text()
    }

    class PluginManager {
        +load_plugins()
        +emit_event()
        +register()
    }

    class Plugin {
        <<abstract>>
        +on_handle_context()
        +on_decorate_reply()
        +on_send_reply()
    }

    class Context {
        +type: ContextType
        +content: str
        +session_id: str
        +receiver: str
        +msg: ChatMessage
        +isgroup: bool
    }

    class Reply {
        +type: ReplyType
        +content: str
        +media_id: str
    }

    Channel <|-- ChatChannel
    ChatChannel <|-- WechatMPChannel

    Bot <|-- ChatGPTBot
    Plugin <|-- HelloPlugin
    Plugin <|-- BanwordsPlugin

    ChatChannel --> Bridge : uses
    Bridge --> Bot : creates
    ChatChannel --> PluginManager : uses
    PluginManager --> Plugin : manages

    ChatChannel --> Context : creates
    ChatChannel --> Reply : handles

    WechatMPChannel --> Context : creates
    Bot --> Reply : returns
```

## 数据流转图

```mermaid
flowchart TD
    subgraph "输入数据"
        INPUT[用户输入<br/>文本/语音/图片]
    end

    subgraph "数据解析"
        PARSE[消息解析<br/>parse_message()]
        MSG[WeChatMPMessage<br/>消息对象]
    end

    subgraph "上下文创建"
        CONTEXT[Context对象<br/>{type, content, session_id, ...}]
    end

    subgraph "插件处理"
        PLUGIN_IN[插件输入处理]
        PLUGIN_OUT[插件输出处理]
    end

    subgraph "AI处理"
        AI_INPUT[AI输入格式化]
        AI_CALL[AI API调用]
        AI_OUTPUT[AI输出解析]
    end

    subgraph "回复生成"
        REPLY[Reply对象<br/>{type, content, media_id}]
    end

    subgraph "输出处理"
        FORMAT[格式化输出]
        SEND[发送处理]
        OUTPUT[用户接收<br/>文本/语音/图片]
    end

    INPUT --> PARSE
    PARSE --> MSG
    MSG --> CONTEXT
    CONTEXT --> PLUGIN_IN
    PLUGIN_IN --> AI_INPUT
    AI_INPUT --> AI_CALL
    AI_CALL --> AI_OUTPUT
    AI_OUTPUT --> REPLY
    REPLY --> PLUGIN_OUT
    PLUGIN_OUT --> FORMAT
    FORMAT --> SEND
    SEND --> OUTPUT

    %% 数据转换标注
    PARSE -.->|JSON解析| MSG
    MSG -.->|属性映射| CONTEXT
    CONTEXT -.->|参数提取| AI_INPUT
    AI_OUTPUT -.->|结果封装| REPLY
    REPLY -.->|类型转换| FORMAT
```

## 配置驱动架构

```mermaid
graph TB
    subgraph "配置文件"
        CONFIG_JSON[config.json<br/>主配置文件]
        PLUGIN_CONFIG[plugins/plugins.json<br/>插件配置]
        ENV_CONFIG[环境变量<br/>运行时配置]
    end

    subgraph "配置加载器"
        LOADER[ConfigLoader<br/>配置加载管理器]
    end

    subgraph "组件配置"
        CHANNEL_CONFIG[Channel配置<br/>通道类型、端口等]
        BOT_CONFIG[Bot配置<br/>模型、API密钥等]
        PLUGIN_CONFIG_MGR[Plugin配置<br/>插件开关、优先级等]
        VOICE_CONFIG[Voice配置<br/>语音服务配置]
    end

    subgraph "运行时组件"
        CHANNEL_FACTORY[ChannelFactory]
        BOT_FACTORY[BotFactory]
        PLUGIN_MANAGER[PluginManager]
        VOICE_FACTORY[VoiceFactory]
    end

    CONFIG_JSON --> LOADER
    PLUGIN_CONFIG --> LOADER
    ENV_CONFIG --> LOADER

    LOADER --> CHANNEL_CONFIG
    LOADER --> BOT_CONFIG
    LOADER --> PLUGIN_CONFIG_MGR
    LOADER --> VOICE_CONFIG

    CHANNEL_CONFIG --> CHANNEL_FACTORY
    BOT_CONFIG --> BOT_FACTORY
    PLUGIN_CONFIG_MGR --> PLUGIN_MANAGER
    VOICE_CONFIG --> VOICE_FACTORY

    %% 当前配置标注
    CHANNEL_CONFIG -.->|channel_type=wechatmp| CHANNEL_FACTORY
    BOT_CONFIG -.->|model=ep-20240629044418-hpqwb| BOT_FACTORY
    VOICE_CONFIG -.->|azure speech services| VOICE_FACTORY
```

此技术架构图清晰地展示了系统的各个层次和组件之间的关系，以及基于当前配置文件的具体执行路径。通过这些图表，可以更好地理解系统的整体设计和运行机制。
