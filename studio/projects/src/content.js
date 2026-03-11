export const siteMeta = {
  title: '数智赋能示范课堂',
  subtitle: '大学生活跃心理支持与互动学习空间',
  description:
    '融合模块学习、智能引导与情景练习的心理健康教育 MVP 站点。',
  footer: {
    stage: '课程体验版 · 内容与交互主链已接通',
    description:
      '本课堂致力于通过数智化手段，将心理健康知识转化为即时可感的支持。我们关注每个学生的微小卡点，并提供安全、专业的引导路径。',
    quickLinks: [
      { label: '主题模块', target: '/modules' },
      { label: '智能助教', target: '/tutor' },
      { label: '风险出口', target: '/risk-help' }
    ],
    commitments: [
      '精准对焦：先识别核心卡点，再给出最小动作建议',
      '知行合一：情景练习入口直达，化认知为实际能力',
      '安全第一：风险动态识别，现实支持始终处于前置位'
    ]
  }
};

export const siteNavigation = [
  { href: '/', label: '首页' },
  { href: '/modules', label: '课程模块' },
  { href: '/tutor', label: '智能助教' },
  { href: '/risk-help', label: '风险帮助' }
];

export const pathwayFlow = {
  title: '识别-行动-练习-安全',
  description:
    '这是整站默认主线路径。先把问题落到具体场景，再拿到动作、做一次模拟；如果状态已经过载，就立刻切到现实支持。',
  stages: [
    {
      id: 'identify',
      kicker: 'Step 1',
      title: '识别当前卡点',
      description: '从首页或模块页先判断自己更像哪类问题，不把困扰继续留在模糊状态。',
      target: '/modules',
      actionLabel: '去看课程模块'
    },
    {
      id: 'guide',
      kicker: 'Step 2',
      title: '让助教拆成动作',
      description: '把眼前最卡的场景交给助教，优先得到一句能立刻执行的话。',
      target: '/tutor',
      actionLabel: '打开智能助教'
    },
    {
      id: 'practice',
      kicker: 'Step 3',
      title: '在练习页先演一遍',
      description: '先在低风险空间里把一句话练顺，把认知转成能带回现实的动作。',
      target: '/practice/exam-reset',
      actionLabel: '进入情景练习'
    },
    {
      id: 'safety',
      kicker: 'Step 4',
      title: '状态过载时切安全出口',
      description: '一旦识别到风险升高，马上回到现实支持，不继续留在站内空转。',
      target: '/risk-help',
      actionLabel: '查看风险帮助'
    }
  ]
};

export const modules = [
  {
    id: 'interpersonal',
    route: '/modules/interpersonal',
    title: '人际交往',
    shortDescription: '在室友沟通、关系边界与拒绝表达中，找回自在的相处方式。',
    subtitle: '让边界清晰，让沟通有度。',
    intro:
      '大学的人际压力往往隐藏在细微的日常摩擦中。本模块带你拆解关系中的“不好意思”与“委屈”，通过具体的表达模版与情景练习，帮你建立健康、有尊严的社交边界。',
    tags: ['沟通技巧', '边界意识', '非暴力表达'],
    problemList: [
      '室友作息不一致，想开口提醒却怕搞僵关系',
      '面对不合理的请求，习惯性答应后又感到疲惫',
      '在群体讨论中，难以清晰表达自己的不同意见',
      '面对冲突倾向于长期隐忍，直至情绪爆发',
      '想拒绝社交邀请，却总在担心他人的评价'
    ],
    insights: [
      {
        title: '事实与感受的分离',
        body: '客观描述正在发生的事实，比直接评价对方的人品更有助于解决问题。'
      },
      {
        title: '边界是尊重的基石',
        body: '清晰地表达你的底线，不是在攻击他人，而是在建立长久关系的契约。'
      },
      {
        title: '冲突的建设性转化',
        body: '适度的、清晰的碰撞，往往能让关系从表面的客气转向深度的理解。'
      }
    ],
    misunderstandings: [
      '“忍一忍就过去了”往往会导致更严重的情绪内耗。',
      '“表达不满等于难搞”是常见的认知偏差，表达是权利。',
      '拒绝别人并不一定会伤害感情，模糊的答应才会。'
    ],
    methods: [
      {
        title: '“我”语境表达法',
        body: '将“你总是...”改为“我感到...，因为...”，降低对方的防御心。'
      },
      {
        title: 'DESC 沟通模型',
        body: '描述(Describe)、表达(Express)、指定(Specify)、结果(Consequence)。'
      }
    ],
    practiceEntries: [
      { id: 'roommate-talk', type: 'scenario', label: '室友作息问题开口练习' }
    ],
    tutorPrompts: [
      '我该如何优雅地拒绝室友的借钱请求？',
      '室友总是半夜打游戏，我该怎么说？',
      '面对舍友的排挤，我该如何稳住心态？'
    ],
    relatedResources: [
      {
        title: '高频社交场景金句包',
        summary: '整理了 10 个最常见的社交卡点表达模版，直接拿来用。'
      }
    ]
  },
  {
    id: 'study-mindset',
    route: '/modules/study-mindset',
    title: '学习心理',
    shortDescription: '应对拖延、考试焦虑与学业压力，重建对学习的掌控感。',
    subtitle: '拆解压力，轻量启动。',
    intro:
      '学业压力的核心往往是对“未知”与“完美”的恐惧。本模块致力于帮你将庞大的任务拆解为可触达的小步，通过调节情绪预期与环境阻力，找回高效、专注的学习节奏。',
    tags: ['习惯养成', '焦虑调节', '专注力'],
    problemList: [
      '明知任务紧迫，却深陷于“刷手机”的逃避循环',
      '面对堆积如山的期末复习，感到无从下手而焦虑',
      '过分追求完美，导致迟迟无法提交第一版草稿',
      '在学习时难以维持专注，极易被各种琐事干扰',
      '一次考试的挫败，让你对自己的能力产生全面怀疑'
    ],
    insights: [
      {
        title: '拖延是情绪调节的代偿',
        body: '当你回避任务时，本质是在回避由于任务带来的焦虑感。'
      },
      {
        title: '微小胜利的累积',
        body: '与其设定一个宏大计划，不如先完成一个 5 分钟就能做完的动作。'
      }
    ],
    misunderstandings: [
      '“我还没准备好”是开始任务的最大谎言，开始就是准备。',
      '压力越大不代表效率越高，适度的放松反而能提升认知资源。',
      '失败只是关于特定任务的反馈，不代表你的人格评价。'
    ],
    methods: [
      {
        title: '原子任务拆解法',
        body: '将大项目拆解为“打开文档”、“写出大纲”等原子级动作。'
      },
      {
        title: '情绪先行的启动术',
        body: '先花 2 分钟平复呼吸，接受“做得不完美”的心理预期再开始。'
      }
    ],
    practiceEntries: [
      { id: 'exam-reset', type: 'scenario', label: '考前混乱状态的断点重连' }
    ],
    tutorPrompts: [
      '我完全看不下书，已经荒废了三天，怎么办？',
      '一想到明天的演讲我就想吐，该怎么缓解？',
      '挂科了，我感觉自己的人生要毁了，救命。'
    ],
    relatedResources: [
      {
        title: '期末周“稳态”生存手册',
        summary: '关于精力分配、任务优先级与紧急降压的系统策略。'
      }
    ]
  },
  {
    id: 'emotion-regulation',
    route: '/modules/emotion-regulation',
    title: '情绪调节',
    shortDescription: '识别、接住并平衡你的情绪，不让它成为行动的阻碍。',
    subtitle: '觉察情绪，平和共处。',
    intro:
      '情绪不是需要被“消灭”的对手，而是关于你内在需求的重要信号。本模块教你如何通过正念觉察、物理降温与认知重构，在情绪浪潮袭来时稳住重心，做出更理性的回应。',
    tags: ['情绪识别', '正念觉察', '心理韧性'],
    problemList: [
      '在压力下极易易怒或委屈，甚至影响到周围的人',
      '长期感到一种莫名的低落，却说不清是因为什么',
      '情绪波动剧烈，难以长时间维持在稳定的工作状态',
      '习惯性压抑负面情绪，直到身体出现不适或突然爆发',
      '对未来的不确定感感到极度不安，反复陷入灾难化思维'
    ],
    insights: [
      {
        title: '命名即掌控',
        body: '当你能准确说出“我现在感到的是无力感”时，你已经从被动卷入转向了主动观察。'
      },
      {
        title: '情绪的冲浪者',
        body: '情绪像海浪，有起有落。你需要做的是学会在浪尖保持平衡，而不是阻止海浪。'
      }
    ],
    misunderstandings: [
      '“正能量”不是唯一的情绪目标，所有的情绪都有其价值。',
      '调节情绪不是压抑情绪，而是寻找更健康的表达和转化出口。',
      '你不需要“立刻恢复正常”，给自己留出感受和消化的空间。'
    ],
    methods: [
      {
        title: '物理断路法',
        body: '在情绪极度高涨时，通过深呼吸、冷水洗脸或离开现场来实现即时降温。'
      },
      {
        title: '三栏思维挑战表',
        body: '记录情绪诱因、自动思维，并尝试写出一个更客观的替代性想法。'
      }
    ],
    practiceEntries: [
      { id: 'emotion-cooldown', type: 'scenario', label: '高强度冲突下的即时降温' }
    ],
    tutorPrompts: [
      '我现在气得发抖，该怎么让自己冷静下来？',
      '我觉得自己什么都做不好，这种挫败感挥之不去。',
      '最近总是想哭，但又不知道为什么，这正常吗？'
    ],
    relatedResources: [
      {
        title: '5分钟正念冥想音频',
        summary: '通过简单的呼吸引导，带你回到此时此地的平静状态。'
      }
    ]
  }
];

export const practices = [
  {
    id: 'roommate-talk',
    route: '/practice/roommate-talk',
    title: '室友沟通实战练习',
    moduleId: 'interpersonal',
    summary: '模拟一次低冲突、高清晰度的边界表达。',
    goal: '在保持关系温度的同时，清晰表达个人需求。',
    context: {
      userRole: '希望调整宿舍环境的你',
      otherRole: '习惯不同的室友',
      situation: '对方习惯在深夜大声语音或开灯，已影响到你的深度睡眠。'
    },
    steps: [
      '陈述事实：描述具体的受影响时间与行为（不带评价）',
      '表达感受：告知这一行为对你生理与心理的具体影响',
      '提出请求：给出一个具体、可操作且可协商的解决方案'
    ],
    coachTips: [
      '尝试将“你太吵了”替换为“昨晚 12 点后宿舍的音量让我很难入睡”。',
      '在提出请求后，询问一句“你觉得这个安排可以吗？”能有效降低对方的抵触感。'
    ],
    sampleLine:
      '“同学，最近我发现 12 点后的开灯和声音对我睡眠影响挺大的，我这两天精神状态不好。咱们能不能商量下，12 点后尽量用台灯并戴上耳机？你觉得怎么样？”',
    feedbackFocus: ['描述的客观性', '表达的真诚度', '方案的可执行性'],
    reflectionQuestions: [
      '在模拟过程中，你感到最难说出口的是哪一部分？',
      '如果对方拒绝了你的请求，你的备选方案是什么？'
    ],
    nextActions: [
      { label: '回模块深化技巧', target: '/modules/interpersonal' },
      { label: '向助教反馈模拟感受', target: '/tutor' }
    ]
  },
  {
    id: 'exam-reset',
    route: '/practice/exam-reset',
    title: '学业混乱状态断点重连',
    moduleId: 'study-mindset',
    summary: '练习如何从焦虑的“空转”状态切换到“微执行”模式。',
    goal: '降低认知负荷，锁定今天能完成的 3 个原子动作。',
    context: {
      userRole: '被任务包围的你',
      otherRole: '焦虑感',
      situation: '面对期末考试或大型项目，你脑中充满了“来不及了”的声音，整个人处于僵持状态。'
    },
    steps: [
      '清空大脑：罗列所有让你担心的任务（不论大小）',
      '极限筛选：从中挑出今天如果不做会有最直接后果的 1 项',
      '原子拆解：将该项拆解为前 15 分钟能立刻开始的微小动作'
    ],
    coachTips: [
      '此时的目标不是“做完”，而是“开始”。',
      '哪怕只是“打开文件夹”或“写出 3 个标题”，也算作成功的断点重连。'
    ],
    sampleLine:
      '“我现在先把明天要考的章节标题列在纸上，然后只读第一章的前两页。”',
    feedbackFocus: ['任务颗粒度', '行动门槛', '心理预期管理'],
    reflectionQuestions: [
      '完成这 15 分钟动作后，你脑中的焦虑音量是否有降低？',
      '是什么因素让你最难迈出这第一步？'
    ],
    nextActions: [
      { label: '回模块看更多方法', target: '/modules/study-mindset' },
      { label: '让助教陪你监督第一步', target: '/tutor' }
    ]
  },
  {
    id: 'emotion-cooldown',
    route: '/practice/emotion-cooldown',
    title: '情绪高压即时降温',
    moduleId: 'emotion-regulation',
    summary: '练习在情绪爆发前，执行有效的生理与心理“阻断”。',
    goal: '在情绪过载时，成功运用物理手段与认知命名稳住重心。',
    context: {
      userRole: '情绪过载的你',
      otherRole: '外部触发点',
      situation: '你刚收到一条让你愤怒的消息，或是在争执中感到心跳加速、手抖，快要失控。'
    },
    steps: [
      '物理撤离：离开高刺激环境（如放下手机、走出房间）',
      '精准命名：在心里对自己说“我现在感到了强烈的愤怒和被羞辱感”',
      '感官锚定：关注此时此刻的呼吸或脚掌接触地面的感觉'
    ],
    coachTips: [
      '命名情绪能让大脑从“负责冲动的边缘系统”切换到“负责理性的前额叶”。',
      '这 30 秒的阻断，往往能避免后面 3 小时的后悔。'
    ],
    sampleLine:
      '“我现在情绪有点上头，咱们先暂停对话 10 分钟，等我稳一下再谈。”',
    feedbackFocus: ['反应的即时性', '动作的纯粹性', '自我察觉的深度'],
    reflectionQuestions: [
      '当你尝试物理撤离时，你感到的阻力是什么？',
      '哪种感官锚定（如呼吸、气味、触感）对你最有效？'
    ],
    nextActions: [
      { label: '回模块看情绪原理', target: '/modules/emotion-regulation' },
      { label: '去助教页做情绪复盘', target: '/tutor' }
    ]
  }
];

export const homePage = {
  hero: {
    kicker: '心理健康教育 · 数智赋能版',
    title: '别让压力，变成你一个人的硬扛',
    subtitle: '数智赋能示范课堂：把课程、助教、练习和安全出口接成一条清晰路径。',
    intro:
      '这里不是冷冰冰的课程目录，更像一个能马上拿来用的支持空间。先帮你识别卡点，再给你一句能行动的话；如果状态已经过载，就把现实支持放到最前面。',
    primaryCta: { label: '马上识别我的卡点', target: '/modules' },
    secondaryCta: { label: '没头绪？先和助教聊', target: '/tutor' },
    metrics: [
      { value: '3', label: '主题模块' },
      { value: '3', label: '情景练习' },
      { value: '24h', label: '安全出口' }
    ],
    supportChips: ['学生视角', '带路式助教', '情景练习', '风险前置']
  },
  heroFlow: [
    '先在首页判断自己更像哪一类卡点',
    '进入对应模块，把困扰拆成可理解的问题',
    '把当前场景带给助教，拿到一句能行动的话',
    '如果状态过载，立刻切到风险帮助与现实支持'
  ],
  heroStatus:
    '当前主链路已打通：内容、助教、练习与风险出口可以直接串联使用。',
  moduleSection: {
    title: '从此刻最关心的主题开始',
    description: '如果你已经大概知道自己卡在哪，就直接进对应主题，不用从头看完。'
  },
  routeSection: {
    title: '四种切入方式，总有一种适合你',
    description: '不管你想系统看、先开口、先练一遍，还是先保安全，这里都有入口。'
  },
  routeCards: [
    {
      title: '我有系统学习的需求',
      description: '从模块页进入，用典型情境、核心认识和误区提醒，先把问题看清。',
      label: '前往课程模块',
      target: '/modules'
    },
    {
      title: '我只想现在练一遍',
      description: '跳过理论，直接做 5 到 10 分钟的小练习，把一句话先说顺。',
      label: '进入情景练习',
      target: '/practice/exam-reset'
    },
    {
      title: '我感到困惑且想倾诉',
      description: '让助教先陪你把问题拆开，再给你最贴近的模块、练习或现实支持入口。',
      label: '由助教带路',
      target: '/tutor'
    }
  ],
  practiceSection: {
    title: '化认知为行动',
    description: '所有改变都先从一个小动作开始。选一个场景，先在安全空间里练一遍。'
  },
  journeySection: {
    title: '如何利用好这个课堂',
    description: '更像一条带路式路径：先确认问题，再拿到动作，最后回到现实生活里用起来。'
  },
  journeySteps: [
    {
      title: '精准定位',
      body: '把模糊的“不舒服”拆成更具体的场景，比如边界冲突、任务空转或情绪过载。'
    },
    {
      title: '获得动作',
      body: '助教先给一个此时此刻就能执行的最小动作，而不是一大段空泛建议。'
    },
    {
      title: '模拟内化',
      body: '练习页提供安全实验场，让你先把那句话练顺，再带回现实情境。'
    },
    {
      title: '安全兜底',
      body: '一旦状态超出站内处理范围，风险帮助页会立刻把现实支持顶到最前面。'
    }
  ],
  tutorEntry: {
    title: '不知道从哪开始？让助教陪你理一理',
    description: '直接把最近最耗能、最卡住的一件事写下来。助教会先帮你判断路径，再给下一步。',
    quickPrompts: [
      '我最近总是无端感到烦躁，该怎么办？',
      '我明早有考试但现在完全看不进去，求救！',
      '想和男朋友谈谈边界问题，不知道怎么开口。'
    ],
    highlights: [
      '语义识别：自动关联最贴近的学习模块',
      '动作导向：每一轮对话都旨在得出下一步',
      '风险监控：敏感表达自动切换现实支持'
    ]
  },
  riskHelp: {
    title: '如果你正经历严重情绪危机或人身危险',
    description: '请停止站内浏览，直接查看这一页。这里有你现在最需要的行动建议与校内外紧急联系方式。',
    actionPoints: ['脱离当前刺激环境', '建立真实的人际联结', '联系校内紧急支持渠道']
  }
};

export const modulesIndexPage = {
  kicker: '课程总览',
  decisionTips: [
    '如果你正因“人际摩擦”或“拒绝太难”而烦恼，请看【人际交往】。',
    '如果你正被“任务堆积”或“效率焦虑”困扰，请看【学习心理】。',
    '如果你感到“情绪过载”或“难以平静”，请看【情绪调节】。'
  ]
};

export const practicePage = {
  kicker: '情景练习',
  heroChecklist: [
    '盯住一个动作：每次练习只尝试改进一句话或一个微小的反应。',
    '允许不完美：模拟的目标是熟悉节奏，而不是做出完美表现。',
    '适时退出：如果练习让你感到压力激增，请直接切换至风险帮助。'
  ]
};

export const tutorPage = {
  kicker: '智能助教',
  title: '智能助教',
  subtitle: '先说出卡点，再拿到能执行的下一步。',
  disclaimer: '助教提供课程辅助与分流建议，不替代专业医疗或心理咨询。',
  roleName: '课程助教',
  roleDescription:
    '我会帮你把混乱的描述拆成场景、情绪和下一步动作，再决定是去模块、练习还是现实支持。',
  flowTitle: '助教会怎么带你走',
  panelNote: '这不是泛聊天窗口。目标是尽快帮你从“卡住”走到“能做一点什么”。',
  stateCopy: {
    welcome: '你好，我是课程助教。比起陪你空转，我更想先和你一起把最耗能的那件事拆清楚。',
    thinking: '我正在判断你说的是情绪过载、关系冲突，还是学业卡壳，然后给你最贴近的动作。',
    medium: '你现在的状态更适合现实支持。我们先把校内外紧急通道顶到最前面。',
    high: '现在先别硬撑。普通对话先停在这里，请优先联系现实中的支持资源。'
  },
  usageSteps: [
    {
      title: '说具体事件',
      body: '不用润色，直接说发生了什么、你卡在哪一刻、最难受的感觉是什么。'
    },
    {
      title: '让我判断路径',
      body: '我会先判断这是更适合去模块、做练习，还是该先切到现实支持。'
    },
    {
      title: '立刻去做下一步',
      body: '拿到一个最小动作后就执行，不把页面停留在“我知道了”这一层。'
    }
  ],
  composerHint: '尽量说具体一点：发生了什么？你最卡的是哪一刻？你现在最难受的感觉是什么？',
  quickPrompts: [
    '我最近压力极大，应该先做什么？',
    '我总是习惯性拖延，怎么打破循环？',
    '我不知道怎么和室友沟通作息问题。',
    '请根据我目前的状态推荐一个练习。'
  ],
  surfaceTags: ['先行动', '带上下文', '风险联动'],
  apiPreparation: {
    title: '系统接入层说明',
    description: '当前版本已打通千问 API 与本地兜底逻辑，保证页面联调和验收可继续推进。',
    checklist: [
      'DASHSCOPE_API_KEY 已完成后端配置校验。',
      '交互接口支持 reply、riskLevel、uiState 的全量下发。',
      '本地兜底逻辑已就绪，确保在网络波动时依然能提供基础引导。'
    ]
  },
  responsePrinciples: [
    '先给动作，再解释原因，避免信息过载',
    '尽量只推一个最相关的入口，不把你再次推回选择困难',
    '一旦识别风险，优先转入现实支持，不继续普通学习流程'
  ]
};

export const riskReasonCopy = {
  'api-error': '助教接口临时不可用，系统已自动将你切换到安全出口页面。',
  'model-risk-detected': '对话中识别到潜在高风险表达，已优先展示现实支持入口。',
  'user-manual-switch': '你主动选择了安全出口，当前页面将优先提供现实支持信息。',
  'context-overload': '当前上下文出现明显过载信号，建议先处理现实安全与稳定。',
  'safety-first': '系统识别到高风险表达，已将安全动作与现实支持置顶。',
  'support-first': '系统识别到中风险状态，建议先联系现实支持后再继续学习。',
  'just-in-case': '当前为低风险状态，此入口作为常驻安全出口保留。',
  'contact-support': '你正在查看“先联系真人支持”的专用入口。',
  'campus-support': '你正在查看校内支持资源入口，请优先使用校方正式渠道。',
  emergency: '你正在查看紧急提醒入口，请优先确认现实安全。',
  'immediate-actions': '你正在查看“先做这几步”动作清单，请先执行最紧急的一步。'
};

export const riskHelpPage = {
  kicker: '安全出口',
  title: '寻求现实支持',
  subtitle: '如果你现在感到极度痛苦、失控，或无法保证安全，请先看这一页。',
  supportPrinciples: [
    {
      title: '先稳住，再谈其他',
      body: '这一刻最重要的不是分析原因，而是先把自己放到更安全、更可被接住的位置。'
    },
    {
      title: '先联系真人',
      body: '去找那个此刻能回应你的人，哪怕只是让对方陪你待一会儿，也比独自硬撑更有效。'
    },
    {
      title: '这页是临时出口',
      body: '站内内容可以稍后再说；只要你觉得顶不住了，就先回到这一页处理现实支持。'
    }
  ],
  immediateActions: [
    '【先离开刺激源】：如果眼前的人、对话或环境让你更难受，请先离开这个空间。',
    '【马上联系一个真人】：现在就给朋友、家人、辅导员或老师发消息，告诉对方你状态不对。',
    '【需要时直接求助】：如果你有伤害自己或他人的冲动，请立刻拨打紧急电话或联系值班老师。'
  ],
  verificationChecklist: [
    '本页信息已按《大学生心理健康教育》课程标准配置。',
    '校内资源需在正式上线前，由各校学工部门填入具体的 24 小时热线与办公地址。',
    '全国心理援助热线为通用版本，已核对。'
  ],
  contactPeople: [
    '校区辅导员 / 班主任', 
    '室友 / 同学 / 身边的好友', 
    '你的家人', 
    '校心理咨询中心的老师', 
    '校区保卫处 / 校医院值班人员'
  ],
  campusSupport: [
    '【预约入口】：校心理中心官方预约平台（请联系辅导员获取具体网址）',
    '【校内热线】：学校专属心理援助电话（24 小时值班）',
    '【紧急值班】：学工部门/保卫处紧急联络中心'
  ],
  externalSupport: [
    '【全国热线】：希望 24 热线 400-161-9995',
    '【心理热线】：国家卫健委心理援助热线 12320',
    '【紧急求助】：110（报警）/ 120（急救）'
  ],
  emergencyNote:
    '重要提醒：如果你已经有明确伤害自己或他人的冲动，或者你无法保证接下来的安全，请务必立刻拨打 110 或联系身边最近的成年人、老师或保安人员。',
  aftercareSteps: [
    '联系到支持后，可以直接说：“我现在状态很不好，需要你陪我一会儿。”',
    '今晚先把目标降到最低，优先保证饮水、进食、睡眠和有人知道你的状态。',
    '等情绪和身体反应稍微降下来后，再考虑是否回到助教页或模块继续之前的学习。'
  ],
  verificationNote:
    '安全配置：以上信息作为示范课堂的标准安全兜底，正式上线时请替换为校方核准数据。'
};

export const notFoundPage = {
  kicker: '404',
  title: '链接已失效或正在建设中',
  description: '别担心，你并没有迷路。尝试从以下主链路重新开始。',
  recoverySteps: [
    '返回课程模块，寻找你感兴趣的主题。',
    '前往智能助教，尝试把你的困惑说出来。',
    '如果你的状态不对，请直接前往风险帮助页。'
  ]
};

export const modulesById = Object.fromEntries(modules.map((item) => [item.id, item]));
export const practicesById = Object.fromEntries(practices.map((item) => [item.id, item]));

export function getModule(id) {
  return modulesById[id] || null;
}

export function getPractice(id) {
  return practicesById[id] || null;
}
