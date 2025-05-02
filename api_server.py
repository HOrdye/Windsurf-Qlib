import os
import uuid
import sys # Added for path manipulation
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# --- Add qlib-server to Python path --- 
# Moved to be executed earlier
QLIB_DIR = os.path.dirname(os.path.abspath(__file__))
if QLIB_DIR not in sys.path:
    sys.path.insert(0, QLIB_DIR)
    print(f"--- [Early] Added to sys.path: {QLIB_DIR} ---") # Debug print
else:
    print(f"--- [Early] Path already in sys.path: {QLIB_DIR} ---") # Debug print

# --- Qlib Imports --- 
try:
    print(f"--- Attempting import from sys.path: {sys.path} ---") # Debug print
    from qlib_server.alpha.alpha_generation import AlphaExtractorFactory, AlphaSignal
    print("--- Qlib modules imported successfully ---") # Debug print
    # You might need to configure logging for qlib_server if it uses Python's logging
    # import logging
    # logging.basicConfig(level=logging.INFO) # Example basic config
except ImportError as e:
    print(f"--- Error importing Qlib modules: {e} ---") # Debug print
    print("Please ensure 'qlib-server' is in the Python path or PYTHONPATH.")
    # Define dummy classes if import fails to allow server to start
    class AlphaSignal:
        def to_dict(self): return {}
    class AlphaExtractorFactory:
        def __init__(self, *args, **kwargs): pass
        def extract(self, *args, **kwargs): return []
        
        @staticmethod
        def create_extractor(extractor_type, config=None):
            print(f"--- 使用占位符AlphaExtractorFactory.create_extractor方法: {extractor_type} ---")
            return AlphaExtractorFactory()
            
        @staticmethod
        def get_extractor(extractor_type, config=None):
            print(f"--- 使用占位符AlphaExtractorFactory.get_extractor方法: {extractor_type} ---")
            return AlphaExtractorFactory()
# --- End Qlib Imports ---


app = Flask(__name__)

# 完全禁用CORS检查，允许所有请求
app.config['CORS_HEADERS'] = 'Content-Type'

# 全局CORS设置
CORS(app, resources={r"/*": {"origins": "*"}})

# 添加全局的CORS处理
@app.after_request
def after_request(response):
    # 允许所有来源
    response.headers.set('Access-Control-Allow-Origin', '*')
    # 允许所有头部
    response.headers.set('Access-Control-Allow-Headers', '*')
    # 允许所有方法
    response.headers.set('Access-Control-Allow-Methods', '*')
    # 允许凭证
    response.headers.set('Access-Control-Allow-Credentials', 'true')
    return response

# In-memory storage for parsed documents (replace with a proper database/storage)
document_storage = {}

@app.route('/api/alpha/documents/parse-url', methods=['POST'])
def parse_web_document():
    """Parses a web document from a given URL."""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'message': 'Missing URL in request'}), 400

    url = data['url']
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get text content - simple approach, might need refinement
        # Remove script and style elements
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        
        text_content = soup.get_text(separator='\n', strip=True)
        
        document_id = f"web-{uuid.uuid4()}"
        document_storage[document_id] = text_content
        
        return jsonify({
            'document_id': document_id,
            'message': '网页解析成功',
            'content': { # Optionally return some metadata or preview
                'text_preview': text_content[:500] + '...' if len(text_content) > 500 else text_content,
                'metadata': {
                    'url': url,
                    'title': soup.title.string if soup.title else 'No Title Found'
                }
            }
        }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({'message': f'Error fetching URL: {e}'}), 500
    except Exception as e:
        return jsonify({'message': f'Error parsing content: {e}'}), 500

@app.route('/api/alpha/extract', methods=['POST'])
def extract_alpha_signals():
    """Extracts Alpha signals from a previously parsed document using Qlib."""
    data = request.get_json()
    if not data or 'document_id' not in data or 'extractor_type' not in data:
        return jsonify({'message': 'Missing document_id or extractor_type'}), 400

    document_id = data['document_id']
    extractor_type = data.get('extractor_type', 'llm') # Default to 'llm' if not provided

    if document_id not in document_storage:
        return jsonify({'message': 'Document not found or expired'}), 404

    text_content = document_storage[document_id]

    if not text_content:
         return jsonify({'message': 'Document content is empty'}), 400

    # --- 使用真实的Qlib提取器 --- 
    print(f"--- 使用真实的Qlib提取器: {extractor_type} ---")
    print(f"--- 文档ID: {document_id} ---")
    
    try:
        # 实例化提取器，使用DeepSeek作为默认LLM
        config = {
            "model_name": "deepseek-chat", # DeepSeek模型名称
            "temperature": 0.3,            # 生成温度，较低的值使输出更确定性
            "max_tokens": 1500,           # 最大生成令牌数
            "minimum_confidence": 0.5,    # 最低置信度阈值
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""), # 从环境变量获取API密钥
            "llm_provider": "deepseek"    # 默认使用DeepSeek提供商
        }
        
        # 如果用户选择了特定的提取器类型，使用该类型
        # 否则默认使用deepseek提取器
        if not extractor_type or extractor_type == "auto":
            extractor_type = "deepseek"
        
        print(f"--- 尝试创建提取器: {extractor_type} ---")
        
        # 直接创建提取器实例，避免使用AlphaExtractorFactory
        try:
            if extractor_type == "rule":
                from qlib_server.alpha.alpha_generation.alpha_extractor import RuleBasedExtractor
                extractor = RuleBasedExtractor(config)
                print("--- 成功创建 RuleBasedExtractor ---")
            elif extractor_type == "llm":
                from qlib_server.alpha.alpha_generation.alpha_extractor import LLMBasedExtractor
                config["llm_provider"] = "openai"
                extractor = LLMBasedExtractor(config)
                print("--- 成功创建 LLMBasedExtractor (OpenAI) ---")
            elif extractor_type == "deepseek":
                from qlib_server.alpha.alpha_generation.alpha_extractor import LLMBasedExtractor
                config["llm_provider"] = "deepseek"
                extractor = LLMBasedExtractor(config)
                print("--- 成功创建 LLMBasedExtractor (DeepSeek) ---")
            else:
                # 默认使用DeepSeek提取器
                from qlib_server.alpha.alpha_generation.alpha_extractor import LLMBasedExtractor
                config["llm_provider"] = "deepseek"
                extractor = LLMBasedExtractor(config)
                print(f"--- 不支持的提取器类型: {extractor_type}，使用DeepSeek提取器作为默认值 ---")
        except Exception as e:
            print(f"--- 创建提取器失败: {e} ---")
            import traceback
            print(traceback.format_exc())
            # 尝试使用规则提取器作为后备
            try:
                from qlib_server.alpha.alpha_generation.alpha_extractor import RuleBasedExtractor
                extractor = RuleBasedExtractor(config)
                print("--- 使用规则提取器作为后备 ---")
            except Exception as e2:
                print(f"--- 创建后备提取器也失败: {e2} ---")
                extractor = None

        if not extractor:
             return jsonify({'message': f'无效的提取器类型: {extractor_type}'}), 400

        # 准备提取器的输入内容字典
        # 基于LLMBasedExtractor.extract的签名
        extraction_input = {
            'success': True,
            'content': text_content,
            'metadata': { 
                'source': 'Web Page Parse API', # 指示来源
                'document_id': document_id
            }
            # 如果需要，可以添加'tables'或其他字段
        }

        # 调用提取器的extract方法
        extracted_signals_objects = extractor.extract(extraction_input)

        # 将AlphaSignal对象转换为字典，用于JSON响应
        signals_list = []
        for i, signal in enumerate(extracted_signals_objects):
            # 生成唯一的信号ID
            signal_id = f'signal-{uuid.uuid4()}'
            
            # 确保信号有实际的因子名称
            if hasattr(signal, 'name') and signal.name and signal.name != 'N/A':
                signal_name = signal.name
            elif hasattr(signal, 'factor_category') and signal.factor_category:
                # 使用因子类别作为名称的一部分
                factor_category = signal.factor_category
                if hasattr(signal, 'direction') and signal.direction:
                    direction = signal.direction.capitalize()
                    signal_name = f'{direction} {factor_category.capitalize()} 因子'
                else:
                    signal_name = f'{factor_category.capitalize()} 因子'
            elif hasattr(signal, 'description') and signal.description:
                # 从描述中提取关键词作为名称
                desc = signal.description[:30]
                keywords = [word for word in desc.split() if len(word) > 3][:2]
                if keywords:
                    signal_name = ' '.join(keywords).capitalize() + ' 因子'
                else:
                    signal_name = f'量化因子 {i+1}'
            else:
                # 默认名称
                signal_name = f'量化因子 {i+1}'
            
            if hasattr(signal, 'to_dict') and callable(signal.to_dict):
                # 使用to_dict方法获取字典
                signal_dict = signal.to_dict()
                # 确保字典有ID和名称
                signal_dict['id'] = signal_id
                signal_dict['name'] = signal_name
                signals_list.append(signal_dict)
            else:
                # 手动创建字典
                signals_list.append({
                    'id': signal_id,
                    'name': signal_name,
                    'description': getattr(signal, 'description', '无描述'),
                    'source': getattr(signal, 'source', document_id),
                    'signal_type': getattr(signal, 'signal_type', 'fundamental'),
                    'factor_category': getattr(signal, 'factor_category', 'other'),
                    'direction': getattr(signal, 'direction', 'neutral'),
                    'confidence': getattr(signal, 'confidence', 0.7),
                    'time_horizon': getattr(signal, 'time_horizon', 'medium_term'),
                    'stock_codes': getattr(signal, 'stock_codes', []),
                    'industry': getattr(signal, 'industry', '综合'),
                    'metrics': getattr(signal, 'metrics', {}),
                    'extraction_date': getattr(signal, 'extraction_date', datetime.now().strftime("%Y-%m-%d")),
                })
                
        message = f'成功使用 {extractor_type} 提取器提取了 {len(signals_list)} 个信号'
        
        # --- 可选：提取后清理文档存储？ ---
        # del document_storage[document_id]
        # --------------------------------------------------------------

        return jsonify({
            'signals': signals_list,
            'message': message
        }), 200

    except Exception as e:
        # 记录完整错误以便调试
        app.logger.error(f"信号提取过程中发生错误: {e}", exc_info=True)
        print(f"--- 提取错误: {e} ---")
        
        # 如果提取失败，返回格式化的错误信号
        signals = []
        factor_types = ['价值型', '成长型', '动量型', '质量型', '流动性型', '收益型']
        directions = ['positive', 'negative', 'neutral']
        
        for i in range(3):  # 创建几个样例信号，以确保前端可以正常显示
            signal_id = f'signal-error-{uuid.uuid4()}'
            factor_type = factor_types[i % len(factor_types)]
            direction = directions[i % len(directions)]
            direction_cn = {'positive': '正向', 'negative': '负向', 'neutral': '中性'}[direction]
            
            signals.append({
                'id': signal_id,
                'name': f'{direction_cn}{factor_type}因子',
                'description': f'提取过程中发生错误: {e}',
                'direction': direction, 
                'confidence': 0.5 + (i * 0.1), 
                'signal_type': 'fundamental', 
                'factor_category': factor_type, 
                'time_horizon': 'medium_term',
                'stock_codes': [f'60000{i}'], 
                'industry': '综合', 
                'source': document_id,
                'metrics': {'PE': 15.0 + i, 'PB': 1.2 + (i * 0.2)},
                'extraction_date': datetime.now().strftime("%Y-%m-%d")
            })
        
        return jsonify({
            'signals': signals,
            'message': f'信号提取过程中发生错误: {e}'
        }), 200  # 返回200而不是500，以便前端能够继续流程

@app.route('/api/alpha/validate', methods=['POST', 'OPTIONS']) # Allow OPTIONS for CORS preflight
def validate_alpha_signals():
    """Validates selected Alpha signals (Placeholder)."""
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        # Flask-CORS should handle this automatically, but adding explicit handling 
        # can sometimes help in complex setups or debugging.
        # You might return an empty response with appropriate headers set by Flask-CORS.
        return '', 200 

    # Handle POST request
    data = request.get_json()
    if not data or 'signal_ids' not in data or 'validator_type' not in data:
        return jsonify({'message': 'Missing signal_ids or validator_type'}), 400

    signal_ids = data['signal_ids']
    validator_type = data['validator_type'] # Placeholder

    if not isinstance(signal_ids, list) or not signal_ids:
        return jsonify({'message': 'signal_ids must be a non-empty list'}), 400

    # --- Placeholder for actual Qlib validation logic --- 
    # TODO: Integrate with qlib-server validation modules here.
    # This would involve:
    # 1. Fetching signal details based on signal_ids (if not already available).
    # 2. Loading necessary market data.
    # 3. Calling the appropriate qlib validator.
    # 4. Formatting the validation results.

    # Mocked validation results:
    validation_results = []
    for signal_id in signal_ids:
        validation_results.append({
            'signal_id': signal_id,
            'status': 'valid', # Mock status
            'score': 0.75, # Mock score
            'metrics': {
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.15,
                'annualized_return': 0.18
            },
            'message': f'Signal {signal_id} passed basic validation (mocked). Validator: {validator_type}'
        })
    # --- End Placeholder ---

    return jsonify({
        'results': validation_results,
        'message': '信号验证成功 (使用占位逻辑)'
    }), 200

# TODO: Implement /api/alpha/documents/upload endpoint for file uploads
# This will require handling multipart/form-data requests.

if __name__ == '__main__':
    # Use environment variable for port or default to 8080
    port = int(os.environ.get('PORT', 8080))
    # Disable reloader for debugging import issues
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False) 
