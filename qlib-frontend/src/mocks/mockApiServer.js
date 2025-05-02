// 模拟API服务器
// 用于测试前端组件与API的交互，无需真实后端

const mockDocuments = [
  {
    document_id: 'doc-001',
    name: '研究报告示例.pdf',
    type: 'pdf',
    upload_time: '2025-04-10T15:30:00Z',
    content: {
      text: '本研究报告分析了近期市场趋势，发现了几个潜在的Alpha因子信号。首先，我们观察到科技板块的估值与历史相比处于较低水平，特别是半导体行业。其次，消费板块中的高端白酒企业显示出较强的盈利能力和现金流。第三，新能源汽车产业链上游的锂电池材料供应商正经历产能扩张，预计将带来业绩增长。基于以上分析，我们建议关注以下几个方向：1）半导体设备制造商；2）高端白酒龙头企业；3）锂电池材料供应商。这些领域可能在未来3-6个月内产生超额收益。',
      metadata: {
        pages: 15,
        author: '量化研究团队',
        date: '2025-04-01'
      }
    }
  },
  {
    document_id: 'doc-002',
    name: '行业分析.docx',
    type: 'docx',
    upload_time: '2025-04-08T10:15:00Z',
    content: {
      text: '本行业分析报告重点研究了医药行业的投资机会。我们发现创新药企业的研发投入与市值比呈现明显的正相关关系，特别是那些拥有突破性新药管线的公司。同时，医疗器械领域中，进口替代趋势明显，国产化率快速提升的细分领域存在投资机会。此外，医疗服务板块中的专科连锁医院模式正在得到市场认可，具有较好的扩张性和盈利能力。基于这些发现，我们认为以下几个因子可能具有较好的预测能力：1）研发投入占比；2）新产品获批数量；3）专利申请增速。',
      metadata: {
        pages: 25,
        author: '医药行业研究员',
        date: '2025-03-15'
      }
    }
  }
];

const mockSignals = [
  {
    id: 'signal-001',
    name: '半导体设备制造商估值因子',
    description: '半导体设备制造商当前估值处于历史低位，但行业景气度开始回升，存在估值修复机会',
    direction: 'positive',
    confidence: 0.85,
    signal_type: 'fundamental',
    factor_category: 'value',
    time_horizon: 'medium_term',
    stock_codes: ['603986', '300316', '002371'],
    industry: '半导体设备',
    source: '研究报告分析',
    metrics: {
      '历史PE分位数': '15%',
      '行业景气度指数': '上升',
      '产能利用率': '65%'
    }
  },
  {
    id: 'signal-002',
    name: '高端白酒盈利能力因子',
    description: '高端白酒企业展现出较强的盈利能力和现金流，在消费升级背景下具有持续增长潜力',
    direction: 'positive',
    confidence: 0.78,
    signal_type: 'fundamental',
    factor_category: 'quality',
    time_horizon: 'long_term',
    stock_codes: ['600519', '000858', '002304'],
    industry: '食品饮料',
    source: '研究报告分析',
    metrics: {
      '毛利率': '75%',
      '净资产收益率': '28%',
      '自由现金流': '增长15%'
    }
  },
  {
    id: 'signal-003',
    name: '锂电池材料供应商产能扩张因子',
    description: '锂电池材料供应商正在扩大产能，预计将带来业绩增长，但需关注供需平衡风险',
    direction: 'positive',
    confidence: 0.65,
    signal_type: 'fundamental',
    factor_category: 'growth',
    time_horizon: 'short_term',
    stock_codes: ['300750', '603799', '002709'],
    industry: '新能源材料',
    source: '研究报告分析',
    metrics: {
      '产能扩张率': '45%',
      '订单增长': '35%',
      '研发投入': '增长25%'
    }
  }
];

const mockValidationResults = [
  {
    signal_id: 'signal-001',
    status: 'passed',
    score: 0.82,
    metrics: {
      'IC值': 0.15,
      'IR值': 1.25,
      '年化收益率': 0.18,
      '最大回撤': -0.12,
      '夏普比率': 1.45
    },
    issues: [],
    recommendations: [
      '可以考虑与动量因子结合使用，提高稳定性',
      '建议在行业轮动策略中使用该因子'
    ]
  },
  {
    signal_id: 'signal-002',
    status: 'passed',
    score: 0.75,
    metrics: {
      'IC值': 0.12,
      'IR值': 1.05,
      '年化收益率': 0.15,
      '最大回撤': -0.10,
      '夏普比率': 1.35
    },
    issues: [],
    recommendations: [
      '适合长期持有策略',
      '建议与估值因子结合使用'
    ]
  },
  {
    signal_id: 'signal-003',
    status: 'warning',
    score: 0.58,
    metrics: {
      'IC值': 0.08,
      'IR值': 0.85,
      '年化收益率': 0.12,
      '最大回撤': -0.18,
      '夏普比率': 0.95
    },
    issues: [
      {
        severity: 'warning',
        message: '因子在市场波动较大时表现不稳定'
      },
      {
        severity: 'warning',
        message: '历史回测期间样本数量较少'
      }
    ],
    recommendations: [
      '建议结合其他因子使用，降低波动性',
      '适合在行业景气度上升阶段使用'
    ]
  }
];

// 模拟API响应
const mockApiResponses = {
  // 上传文档
  uploadDocument: (file, documentType) => {
    return {
      status: 200,
      data: {
        document_id: `doc-${Date.now()}`,
        content: {
          text: file ? `${file.name}的内容示例，这是一个${documentType}文档...` : '文档内容示例',
          metadata: {
            pages: 10,
            author: '示例作者',
            date: new Date().toISOString().split('T')[0]
          }
        },
        message: '文档上传成功'
      }
    };
  },
  
  // 解析网页文档
  parseWebDocument: (url) => {
    return {
      status: 200,
      data: {
        document_id: `web-${Date.now()}`,
        content: {
          text: `从URL ${url} 解析的网页内容示例...这篇文章分析了市场趋势，发现了几个潜在的Alpha因子信号。`,
          metadata: {
            url: url,
            title: 'Web文档示例',
            date: new Date().toISOString().split('T')[0]
          }
        },
        message: '网页解析成功'
      }
    };
  },
  
  // 提取Alpha信号
  extractAlphaSignals: (documentId, extractorType) => {
    // 根据提取器类型返回不同数量的信号
    let signals = [];
    switch (extractorType) {
      case 'rule':
        signals = mockSignals.slice(0, 2);
        break;
      case 'llm':
        signals = mockSignals.slice(0, 3);
        break;
      case 'ensemble':
        signals = mockSignals;
        break;
      default:
        signals = mockSignals.slice(0, 1);
    }
    
    return {
      status: 200,
      data: {
        signals: signals.map(signal => ({
          ...signal,
          id: `${signal.id}-${Date.now()}`
        })),
        message: '信号提取成功'
      }
    };
  },
  
  // 验证Alpha信号
  validateAlphaSignals: (signalIds, validatorType) => {
    // 根据验证器类型返回不同的验证结果
    let results = [];
    if (validatorType === 'basic') {
      results = mockValidationResults.map(result => ({
        ...result,
        metrics: {
          'IC值': result.metrics['IC值'],
          'IR值': result.metrics['IR值']
        }
      }));
    } else {
      results = mockValidationResults;
    }
    
    return {
      status: 200,
      data: {
        results: results.slice(0, signalIds.length),
        message: '信号验证成功'
      }
    };
  },
  
  // 导出Alpha信号
  exportAlphaSignalsToCsv: (signalIds) => {
    // 创建CSV内容
    const headers = 'ID,名称,方向,置信度,类型,时间范围\n';
    const rows = mockSignals
      .filter(signal => signalIds.includes(signal.id))
      .map(signal => `${signal.id},${signal.name},${signal.direction},${signal.confidence},${signal.signal_type},${signal.time_horizon}`)
      .join('\n');
    
    const csvContent = headers + rows;
    
    // 创建Blob对象
    const blob = new Blob([csvContent], { type: 'text/csv' });
    
    return {
      status: 200,
      data: blob,
      message: '信号导出成功'
    };
  }
};

export default mockApiResponses;
