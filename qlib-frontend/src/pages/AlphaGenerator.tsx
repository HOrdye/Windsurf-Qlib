import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Card, 
  Steps, 
  Button, 
  Row, 
  Col, 
  Spin,
  message,
  Space
} from 'antd';
import qlibApi from '../api/qlibApi';
import DocumentUploader from '../components/alpha/DocumentUploader';
import ExtractorSelector from '../components/alpha/ExtractorSelector';
import SignalValidator from '../components/alpha/SignalValidator';
import SignalResults from '../components/alpha/SignalResults';

const { Title, Paragraph } = Typography;
const { Step } = Steps;

// 步骤定义
const steps = ['上传文档', '选择提取器', '验证信号', '查看结果'];

/**
 * Alpha因子生成器页面组件
 * 实现文档上传、信号提取和验证的完整流程
 */
const AlphaGenerator: React.FC = () => {
  // 状态管理
  const [activeStep, setActiveStep] = useState(0);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [documentContent, setDocumentContent] = useState<any>(null);
  const [extractorType, setExtractorType] = useState<string>('rule');
  const [extractedSignals, setExtractedSignals] = useState<any[]>([]);
  const [validatedSignals, setValidatedSignals] = useState<any[]>([]);
  const [selectedSignalIds, setSelectedSignalIds] = useState<string[]>([]);
  const [validatorType, setValidatorType] = useState<string>('basic');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 处理文档上传成功
  const handleDocumentUploaded = (docId: string, content: any) => {
    setDocumentId(docId);
    setDocumentContent(content);
    setSuccess('文档上传成功');
  };

  // 处理提取器选择
  const handleExtractorSelected = (type: string) => {
    setExtractorType(type);
  };

  // 处理信号提取
  const handleExtractSignals = async () => {
    if (!documentId) {
      message.error('请先上传文档');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await qlibApi.extractAlphaSignals(documentId, extractorType);
      setExtractedSignals(response.data.signals || []);
      setSelectedSignalIds(response.data.signals.map((s: any) => s.id));
      message.success('Alpha信号提取成功');
      handleNext();
    } catch (err) {
      message.error('提取Alpha信号失败，请重试');
      console.error('提取信号错误:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 处理信号验证
  const handleValidateSignals = async () => {
    if (selectedSignalIds.length === 0) {
      message.error('请至少选择一个信号进行验证');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await qlibApi.validateAlphaSignals(selectedSignalIds, validatorType);
      setValidatedSignals(response.data.results || []);
      message.success('Alpha信号验证成功');
      handleNext();
    } catch (err) {
      message.error('验证Alpha信号失败，请重试');
      console.error('验证信号错误:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 处理信号选择
  const handleSignalSelection = (signalIds: string[]) => {
    setSelectedSignalIds(signalIds);
  };

  // 处理验证器选择
  const handleValidatorSelected = (type: string) => {
    setValidatorType(type);
  };

  // 导出信号结果为CSV
  const handleExportToCsv = async () => {
    if (selectedSignalIds.length === 0) {
      message.error('请至少选择一个信号进行导出');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await qlibApi.exportAlphaSignalsToCsv(selectedSignalIds);
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `alpha_signals_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      message.success('Alpha信号导出成功');
    } catch (err) {
      message.error('导出Alpha信号失败，请重试');
      console.error('导出信号错误:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 下一步
  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  // 上一步
  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  // 重置流程
  const handleReset = () => {
    setActiveStep(0);
    setDocumentId(null);
    setDocumentContent(null);
    setExtractedSignals([]);
    setValidatedSignals([]);
    setSelectedSignalIds([]);
  };

  // 关闭提示
  const handleCloseAlert = () => {
    setError(null);
    setSuccess(null);
  };

  // 渲染当前步骤内容
  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <DocumentUploader 
            onDocumentUploaded={handleDocumentUploaded} 
            documentContent={documentContent}
          />
        );
      case 1:
        return (
          <ExtractorSelector 
            onExtractorSelected={handleExtractorSelected} 
            extractorType={extractorType}
            documentContent={documentContent}
          />
        );
      case 2:
        return (
          <SignalValidator 
            signals={extractedSignals}
            onSignalSelection={handleSignalSelection}
            selectedSignalIds={selectedSignalIds}
            onValidatorSelected={handleValidatorSelected}
            validatorType={validatorType}
          />
        );
      case 3:
        return (
          <SignalResults 
            signals={extractedSignals}
            validationResults={validatedSignals}
            onExportToCsv={handleExportToCsv}
          />
        );
      default:
        return '未知步骤';
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={2} style={{ textAlign: 'center', marginBottom: 24 }}>Alpha因子生成器</Title>
        
        <Steps current={activeStep} style={{ marginBottom: 32 }}>
          {steps.map((item) => (
            <Step key={item} title={item} />
          ))}
        </Steps>
        
        <div style={{ marginBottom: 24, minHeight: 300 }}>
          {activeStep === steps.length ? (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <Title level={4}>Alpha因子生成完成</Title>
              <Paragraph>您已成功生成并验证Alpha因子信号。</Paragraph>
              <Button type="primary" onClick={handleReset}>
                开始新的生成流程
              </Button>
            </div>
          ) : (
            getStepContent(activeStep)
          )}
        </div>
        
        {activeStep < steps.length && (
          <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
            <Button 
              onClick={handleBack}
              disabled={activeStep === 0 || isLoading}
            >
              上一步
            </Button>
            <Button 
              type="primary"
              onClick={
                activeStep === 0 ? handleNext :
                activeStep === 1 ? handleExtractSignals :
                activeStep === 2 ? handleValidateSignals :
                handleNext
              }
              disabled={isLoading}
            >
              {isLoading ? <Spin size="small" /> : null}
              {activeStep === steps.length - 1 ? '完成' : '下一步'}
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
};

export default AlphaGenerator;
