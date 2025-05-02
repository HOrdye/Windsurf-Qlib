import React, { useState, useRef } from 'react';
import { 
  Typography, 
  Button, 
  Input, 
  Row, 
  Col, 
  Card, 
  Select, 
  Upload, 
  Spin,
  Divider,
  Alert,
  Space
} from 'antd';
import { 
  CloudUploadOutlined, 
  LinkOutlined 
} from '@ant-design/icons';
import qlibApi from '../../api/qlibApi';
import type { UploadProps, RadioChangeEvent } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// 组件属性接口定义
interface DocumentUploaderProps {
  onDocumentUploaded: (documentId: string, content: any) => void;
  documentContent: any;
}

/**
 * 文档上传组件
 * 支持上传PDF、Word文档以及通过URL解析网页
 */
const DocumentUploader: React.FC<DocumentUploaderProps> = ({ onDocumentUploaded, documentContent }) => {
  // 状态管理
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<string>('pdf');
  const [webUrl, setWebUrl] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadMethod, setUploadMethod] = useState<'file' | 'url'>('file');
  const [error, setError] = useState<string | null>(null);
  
  // 文件输入引用
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  // 处理文档类型变更
  const handleDocumentTypeChange = (value: string) => {
    setDocumentType(value);
  };

  // 处理URL输入变更
  const handleUrlChange = (e: any) => {
    setWebUrl(e.target.value);
  };

  // 处理上传方式切换
  const handleUploadMethodChange = (method: 'file' | 'url') => {
    setUploadMethod(method);
    setError(null);
  };

  // 上传文件
  const handleUpload = async () => {
    setError(null);
    setIsUploading(true);
    console.log('[handleUpload] Started. Method:', uploadMethod); // Log start

    try {
      let response;

      if (uploadMethod === 'file') {
        // 文件上传
        console.log('[handleUpload] File upload selected.');
        if (!selectedFile) {
          console.log('[handleUpload] No file selected.');
          setError('请选择要上传的文件');
          setIsUploading(false);
          return;
        }
        console.log('[handleUpload] Calling qlibApi.uploadDocument...');
        response = await qlibApi.uploadDocument(selectedFile, documentType);
        console.log('[handleUpload] qlibApi.uploadDocument response:', response); // Log response

      } else {
        // URL解析
        console.log('[handleUpload] URL parsing selected. URL:', webUrl);
        if (!webUrl) {
          console.log('[handleUpload] No URL entered.');
          setError('请输入有效的网页URL');
          setIsUploading(false);
          return;
        }
        console.log('[handleUpload] Calling qlibApi.parseWebDocument...');
        response = await qlibApi.parseWebDocument(webUrl);
        console.log('[handleUpload] qlibApi.parseWebDocument response:', response); // Log response
      }

      // 处理上传/解析成功
      console.log('[handleUpload] Checking response structure...');
      // Assuming qlibApi uses Axios or similar, response payload is in response.data
      if (response && response.data && response.data.document_id && response.data.content) {
         console.log('[handleUpload] Response OK. Calling onDocumentUploaded with:', response.data.document_id, response.data.content);
        onDocumentUploaded(response.data.document_id, response.data.content);
      } else {
        console.log('[handleUpload] Response structure invalid or missing data.', response);
        setError('文档处理失败，响应数据无效，请重试');
      }
    } catch (err: any) { // Add type 'any' or 'Error'
      console.error('[handleUpload] Error caught:', err);
      // Try to get more specific error message from Axios error object
      const errorMessage = err.response?.data?.error || err.message || '文档上传/解析失败，请检查输入或网络连接';
      console.error('[handleUpload] Setting error message:', errorMessage);
      setError(errorMessage);
    } finally {
      console.log('[handleUpload] Finished.');
      setIsUploading(false);
    }
  };

  // 渲染文档预览
  const renderDocumentPreview = () => {
    if (!documentContent) return null;

    return (
      <div style={{ marginTop: 24 }}>
        <Title level={5}>文档预览</Title>
        <Card style={{ maxHeight: 300, overflow: 'auto' }}>
          {documentContent.text ? (
            <Paragraph>{documentContent.text.substring(0, 1000)}...</Paragraph>
          ) : (
            <Text type="secondary">无法预览文档内容</Text>
          )}
        </Card>
      </div>
    );
  };

  // 自定义上传按钮
  const uploadButton = (
    <div>
      {isUploading ? <Spin /> : <CloudUploadOutlined style={{ fontSize: 32 }} />}
      <div style={{ marginTop: 8 }}>点击上传</div>
    </div>
  );

  return (
    <div>
      <Title level={5}>上传文档</Title>
      
      {/* 上传方式选择 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'center' }}>
        <Button 
          type={uploadMethod === 'file' ? 'primary' : 'default'}
          onClick={() => handleUploadMethodChange('file')}
          style={{ marginRight: 8 }}
        >
          上传文件
        </Button>
        <Button 
          type={uploadMethod === 'url' ? 'primary' : 'default'}
          onClick={() => handleUploadMethodChange('url')}
        >
          解析网页
        </Button>
      </div>
      
      <Divider />
      
      {uploadMethod === 'file' ? (
        <Row gutter={16}>
          <Col span={24}>
            <Upload.Dragger
              name="file"
              multiple={false}
              showUploadList={false}
              beforeUpload={() => false}
              onChange={handleFileSelect}
              accept=".pdf,.docx,.doc"
            >
              {selectedFile ? (
                <div>
                  <CloudUploadOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                  <div style={{ marginTop: 8 }}>{selectedFile.name}</div>
                </div>
              ) : (
                <>
                  <p className="ant-upload-drag-icon">
                    <CloudUploadOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击选择文件或拖放文件至此处</p>
                  <p className="ant-upload-hint">
                    支持PDF和Word文档 (.pdf, .docx, .doc)
                  </p>
                </>
              )}
            </Upload.Dragger>
          </Col>
          
          <Col span={24} style={{ marginTop: 16 }}>
            <Select
              style={{ width: '100%' }}
              value={documentType}
              onChange={handleDocumentTypeChange}
              placeholder="选择文档类型"
            >
              <Option value="pdf">PDF文档</Option>
              <Option value="docx">Word文档</Option>
            </Select>
          </Col>
        </Row>
      ) : (
        <Row gutter={16}>
          <Col span={24}>
            <Input
              placeholder="https://example.com/research-report"
              value={webUrl}
              onChange={handleUrlChange}
              prefix={<LinkOutlined />}
              size="large"
            />
            <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
              输入包含Alpha因子信息的研究报告或新闻文章URL
            </Text>
          </Col>
        </Row>
      )}
      
      {error && (
        <Alert 
          message={error} 
          type="error" 
          showIcon 
          style={{ marginTop: 16 }} 
        />
      )}
      
      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Button
          type="primary"
          onClick={handleUpload}
          disabled={isUploading || (uploadMethod === 'file' && !selectedFile) || (uploadMethod === 'url' && !webUrl)}
          loading={isUploading}
          size="large"
        >
          {isUploading ? '处理中...' : '上传文档'}
        </Button>
      </div>
      
      {renderDocumentPreview()}
    </div>
  );
};

export default DocumentUploader;
