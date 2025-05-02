import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Button, 
  Space, 
  Divider, 
  message, 
  Upload, 
  Input, 
  Select, 
  Table, 
  Tag, 
  Collapse,
  Alert,
  Row,
  Col,
  Spin
} from 'antd';
import { UploadOutlined, LinkOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import qlibApi from '../api/qlibApi';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

/**
 * Alpha因子生成器API集成测试组件
 * 用于测试前端组件与后端API的交互
 */
const AlphaGeneratorApiTest: React.FC = () => {
  // 状态管理
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<string>('pdf');
  const [webUrl, setWebUrl] = useState<string>('');
  const [uploadMethod, setUploadMethod] = useState<'file' | 'url'>('file');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [documentContent, setDocumentContent] = useState<any>(null);
  
  const [extractorType, setExtractorType] = useState<string>('rule');
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const [extractedSignals, setExtractedSignals] = useState<any[]>([]);
  
  const [validatorType, setValidatorType] = useState<string>('basic');
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validationResults, setValidationResults] = useState<any[]>([]);
  
  const [testResults, setTestResults] = useState<{
    upload: { status: 'pending' | 'success' | 'error', message: string },
    extract: { status: 'pending' | 'success' | 'error', message: string },
    validate: { status: 'pending' | 'success' | 'error', message: string },
    export: { status: 'pending' | 'success' | 'error', message: string }
  }>({
    upload: { status: 'pending', message: '未测试' },
    extract: { status: 'pending', message: '未测试' },
    validate: { status: 'pending', message: '未测试' },
    export: { status: 'pending', message: '未测试' }
  });
  
  // 处理文件选择
  const handleFileSelect = (info: any) => {
    if (info.file && info.file.originFileObj) {
      const file = info.file.originFileObj;
      setSelectedFile(file);
      
      // 根据文件类型自动设置文档类型
      if (file.name.toLowerCase().endsWith('.pdf')) {
        setDocumentType('pdf');
      } else if (file.name.toLowerCase().endsWith('.docx') || file.name.toLowerCase().endsWith('.doc')) {
        setDocumentType('docx');
      }
    }
  };
  
  // 处理URL输入变更
  const handleUrlChange = (e: any) => {
    setWebUrl(e.target.value);
  };
  
  // 处理上传方式切换
  const handleUploadMethodChange = (method: 'file' | 'url') => {
    setUploadMethod(method);
    setUploadError(null);
  };
  
  // 测试文档上传API
  const testDocumentUpload = async () => {
    setIsUploading(true);
    setUploadError(null);
    
    try {
      let response;
      
      if (uploadMethod === 'file') {
        // 文件上传
        if (!selectedFile) {
          throw new Error('请选择要上传的文件');
        }
        
        response = await qlibApi.uploadDocument(selectedFile, documentType);
      } else {
        // URL解析
        if (!webUrl) {
          throw new Error('请输入有效的网页URL');
        }
        
        response = await qlibApi.parseWebDocument(webUrl);
      }
      
      // 处理上传/解析成功
      if (response && response.data) {
        setDocumentId(response.data.document_id);
        setDocumentContent(response.data.content);
        setTestResults(prev => ({
          ...prev,
          upload: { status: 'success', message: '文档上传成功' }
        }));
        message.success('文档上传测试成功');
      } else {
        throw new Error('文档处理失败，响应数据无效');
      }
    } catch (err: any) {
      console.error('文档上传错误:', err);
      setUploadError(err.message || '文档上传失败');
      setTestResults(prev => ({
        ...prev,
        upload: { status: 'error', message: err.message || '文档上传失败' }
      }));
      message.error('文档上传测试失败');
    } finally {
      setIsUploading(false);
    }
  };
  
  // 测试Alpha信号提取API
  const testExtractAlphaSignals = async () => {
    if (!documentId) {
      message.warning('请先上传文档');
      return;
    }
    
    setIsExtracting(true);
    setExtractionError(null);
    
    try {
      const response = await qlibApi.extractAlphaSignals(documentId, extractorType);
      
      if (response && response.data && response.data.signals) {
        setExtractedSignals(response.data.signals);
        setTestResults(prev => ({
          ...prev,
          extract: { status: 'success', message: '信号提取成功' }
        }));
        message.success('信号提取测试成功');
      } else {
        throw new Error('信号提取失败，响应数据无效');
      }
    } catch (err: any) {
      console.error('信号提取错误:', err);
      setExtractionError(err.message || '信号提取失败');
      setTestResults(prev => ({
        ...prev,
        extract: { status: 'error', message: err.message || '信号提取失败' }
      }));
      message.error('信号提取测试失败');
    } finally {
      setIsExtracting(false);
    }
  };
  
  // 测试Alpha信号验证API
  const testValidateAlphaSignals = async () => {
    if (extractedSignals.length === 0) {
      message.warning('请先提取信号');
      return;
    }
    
    setIsValidating(true);
    setValidationError(null);
    
    try {
      const signalIds = extractedSignals.map(signal => signal.id);
      const response = await qlibApi.validateAlphaSignals(signalIds, validatorType);
      
      if (response && response.data && response.data.results) {
        setValidationResults(response.data.results);
        setTestResults(prev => ({
          ...prev,
          validate: { status: 'success', message: '信号验证成功' }
        }));
        message.success('信号验证测试成功');
      } else {
        throw new Error('信号验证失败，响应数据无效');
      }
    } catch (err: any) {
      console.error('信号验证错误:', err);
      setValidationError(err.message || '信号验证失败');
      setTestResults(prev => ({
        ...prev,
        validate: { status: 'error', message: err.message || '信号验证失败' }
      }));
      message.error('信号验证测试失败');
    } finally {
      setIsValidating(false);
    }
  };
  
  // 测试导出Alpha信号API
  const testExportAlphaSignals = async () => {
    if (extractedSignals.length === 0) {
      message.warning('请先提取信号');
      return;
    }
    
    try {
      const signalIds = extractedSignals.map(signal => signal.id);
      const response = await qlibApi.exportAlphaSignalsToCsv(signalIds);
      
      if (response && response.data) {
        // 创建Blob对象并下载
        const blob = new Blob([response.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'alpha_signals.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setTestResults(prev => ({
          ...prev,
          export: { status: 'success', message: '信号导出成功' }
        }));
        message.success('信号导出测试成功');
      } else {
        throw new Error('信号导出失败，响应数据无效');
      }
    } catch (err: any) {
      console.error('信号导出错误:', err);
      setTestResults(prev => ({
        ...prev,
        export: { status: 'error', message: err.message || '信号导出失败' }
      }));
      message.error('信号导出测试失败');
    }
  };
  
  // 运行所有测试
  const runAllTests = async () => {
    // 重置测试结果
    setTestResults({
      upload: { status: 'pending', message: '测试中...' },
      extract: { status: 'pending', message: '测试中...' },
      validate: { status: 'pending', message: '测试中...' },
      export: { status: 'pending', message: '测试中...' }
    });
    
    // 顺序执行测试
    await testDocumentUpload();
    
    // 如果上传成功，继续测试提取
    if (documentId) {
      await testExtractAlphaSignals();
      
      // 如果提取成功，继续测试验证
      if (extractedSignals.length > 0) {
        await testValidateAlphaSignals();
        
        // 如果验证成功，继续测试导出
        if (validationResults.length > 0) {
          await testExportAlphaSignals();
        }
      }
    }
  };
  
  // 渲染测试状态标签
  const renderStatusTag = (status: 'pending' | 'success' | 'error') => {
    switch (status) {
      case 'success':
        return <Tag color="success">成功</Tag>;
      case 'error':
        return <Tag color="error">失败</Tag>;
      default:
        return <Tag color="default">未测试</Tag>;
    }
  };
  
  // 渲染文档预览
  const renderDocumentPreview = () => {
    if (!documentContent) return null;
    
    return (
      <div style={{ marginTop: 16 }}>
        <Title level={5}>文档内容预览</Title>
        <Card style={{ maxHeight: 200, overflow: 'auto' }}>
          {documentContent.text ? (
            <Paragraph>{documentContent.text.substring(0, 500)}...</Paragraph>
          ) : (
            <Text type="secondary">无法预览文档内容</Text>
          )}
        </Card>
      </div>
    );
  };
  
  // 渲染信号预览
  const renderSignalsPreview = () => {
    if (extractedSignals.length === 0) return null;
    
    return (
      <div style={{ marginTop: 16 }}>
        <Title level={5}>提取的Alpha信号</Title>
        <Table
          dataSource={extractedSignals.map((signal, index) => ({ ...signal, key: index }))}
          columns={[
            { title: '信号名称', dataIndex: 'name', key: 'name' },
            { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
            { title: '方向', dataIndex: 'direction', key: 'direction' },
            { title: '置信度', dataIndex: 'confidence', key: 'confidence', render: (val) => `${(val * 100).toFixed(0)}%` }
          ]}
          pagination={false}
          size="small"
        />
      </div>
    );
  };
  
  // 渲染验证结果预览
  const renderValidationPreview = () => {
    if (validationResults.length === 0) return null;
    
    return (
      <div style={{ marginTop: 16 }}>
        <Title level={5}>验证结果</Title>
        <Table
          dataSource={validationResults.map((result, index) => ({ ...result, key: index }))}
          columns={[
            { title: '信号ID', dataIndex: 'signal_id', key: 'signal_id' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (status) => (
              <Tag color={status === 'passed' ? 'success' : status === 'warning' ? 'warning' : 'error'}>
                {status === 'passed' ? '通过' : status === 'warning' ? '警告' : '失败'}
              </Tag>
            )},
            { title: '分数', dataIndex: 'score', key: 'score', render: (val) => val ? val.toFixed(2) : 'N/A' }
          ]}
          pagination={false}
          size="small"
        />
      </div>
    );
  };
  
  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>Alpha因子生成器API集成测试</Title>
      <Paragraph>
        此组件用于测试Alpha因子生成器前端组件与后端API的交互。
        按照上传文档、提取信号、验证信号、导出结果的顺序进行测试。
      </Paragraph>
      
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="测试结果摘要">
            <Table
              dataSource={[
                { key: 'upload', name: '文档上传', status: testResults.upload.status, message: testResults.upload.message },
                { key: 'extract', name: '信号提取', status: testResults.extract.status, message: testResults.extract.message },
                { key: 'validate', name: '信号验证', status: testResults.validate.status, message: testResults.validate.message },
                { key: 'export', name: '信号导出', status: testResults.export.status, message: testResults.export.message }
              ]}
              columns={[
                { title: '测试项', dataIndex: 'name', key: 'name' },
                { title: '状态', dataIndex: 'status', key: 'status', render: (status) => renderStatusTag(status) },
                { title: '消息', dataIndex: 'message', key: 'message' }
              ]}
              pagination={false}
              size="small"
            />
            
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Button type="primary" onClick={runAllTests} size="large">
                运行所有测试
              </Button>
            </div>
          </Card>
        </Col>
        
        <Col span={24}>
          <Collapse defaultActiveKey={['1']}>
            <Panel header="1. 文档上传测试" key="1">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Space>
                    <Button 
                      type={uploadMethod === 'file' ? 'primary' : 'default'}
                      onClick={() => handleUploadMethodChange('file')}
                    >
                      上传文件
                    </Button>
                    <Button 
                      type={uploadMethod === 'url' ? 'primary' : 'default'}
                      onClick={() => handleUploadMethodChange('url')}
                    >
                      解析网页
                    </Button>
                  </Space>
                </div>
                
                {uploadMethod === 'file' ? (
                  <div>
                    <Upload
                      beforeUpload={() => false}
                      onChange={handleFileSelect}
                      showUploadList={false}
                    >
                      <Button icon={<UploadOutlined />}>选择文件</Button>
                    </Upload>
                    {selectedFile && (
                      <Text style={{ marginLeft: 8 }}>{selectedFile.name}</Text>
                    )}
                    
                    <div style={{ marginTop: 8 }}>
                      <Select
                        style={{ width: 200 }}
                        value={documentType}
                        onChange={(value) => setDocumentType(value)}
                      >
                        <Option value="pdf">PDF文档</Option>
                        <Option value="docx">Word文档</Option>
                      </Select>
                    </div>
                  </div>
                ) : (
                  <div>
                    <Input
                      placeholder="https://example.com/research-report"
                      value={webUrl}
                      onChange={handleUrlChange}
                      prefix={<LinkOutlined />}
                      style={{ width: '100%' }}
                    />
                  </div>
                )}
                
                {uploadError && (
                  <Alert message={uploadError} type="error" showIcon />
                )}
                
                <Button 
                  type="primary" 
                  onClick={testDocumentUpload}
                  loading={isUploading}
                  disabled={
                    (uploadMethod === 'file' && !selectedFile) || 
                    (uploadMethod === 'url' && !webUrl)
                  }
                >
                  测试文档上传
                </Button>
                
                {renderDocumentPreview()}
              </Space>
            </Panel>
            
            <Panel header="2. 信号提取测试" key="2">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text>选择提取器类型:</Text>
                  <Select
                    style={{ width: 200, marginLeft: 8 }}
                    value={extractorType}
                    onChange={(value) => setExtractorType(value)}
                  >
                    <Option value="rule">规则提取器</Option>
                    <Option value="llm">LLM提取器</Option>
                    <Option value="ensemble">集成提取器</Option>
                  </Select>
                </div>
                
                {extractionError && (
                  <Alert message={extractionError} type="error" showIcon />
                )}
                
                <Button 
                  type="primary" 
                  onClick={testExtractAlphaSignals}
                  loading={isExtracting}
                  disabled={!documentId}
                >
                  测试信号提取
                </Button>
                
                {renderSignalsPreview()}
              </Space>
            </Panel>
            
            <Panel header="3. 信号验证测试" key="3">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text>选择验证器类型:</Text>
                  <Select
                    style={{ width: 200, marginLeft: 8 }}
                    value={validatorType}
                    onChange={(value) => setValidatorType(value)}
                  >
                    <Option value="basic">基础验证器</Option>
                    <Option value="backtest">回测验证器</Option>
                  </Select>
                </div>
                
                {validationError && (
                  <Alert message={validationError} type="error" showIcon />
                )}
                
                <Button 
                  type="primary" 
                  onClick={testValidateAlphaSignals}
                  loading={isValidating}
                  disabled={extractedSignals.length === 0}
                >
                  测试信号验证
                </Button>
                
                {renderValidationPreview()}
              </Space>
            </Panel>
            
            <Panel header="4. 信号导出测试" key="4">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button 
                  type="primary" 
                  onClick={testExportAlphaSignals}
                  disabled={extractedSignals.length === 0}
                >
                  测试信号导出
                </Button>
                
                <Text type="secondary">
                  导出成功后将自动下载CSV文件
                </Text>
              </Space>
            </Panel>
          </Collapse>
        </Col>
      </Row>
    </div>
  );
};

export default AlphaGeneratorApiTest;
