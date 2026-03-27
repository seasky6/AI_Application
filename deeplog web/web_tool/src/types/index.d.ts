// 解析日志类型
export type ZipKind = 'proactive' | 'return';

// 内容抽取
export interface ExtractedEntry {
    AuditDate: string;      // ISO: YYYY-MM-DDTHH:mm:ss
    Serial: string | null;
    ProductName: string | null;
    log_type: 'elog' | 'hwlog' | 'vsread' | 'csread' | 'tsread' | 'trx_status' | string;
    log_line: string;
    LNH: string;
}

// 条目解析
export interface LogEntry {
    Index: number;
    Serial: string;
    ProductName: string;
    LogType: string;
    Timestamp: string;
    LogID: string;
    Content: string;        // 原始内容
    Slogan: string;
    Key: string;
    Value: string | number | boolean | number[]; // 统一存储
    ValueType: ''|'string'|'int'|'float'|'bool'|'List[int]'|'str'|'dict';
    IsMeasuredValue: boolean;
    ParentIndex: number;
}

// PA异常预测：条目样本生成
export interface PaSample {
    Serial: string;               // 串号(仅为目标串号生成)
    ProductName: string;
    Timestamp: string;            // 日志发生时间戳(取 log10 的时间戳)
    parameters: Record<string, any>;
    source_file: string;          // 来源的 *_parsed.json 文件名(便于追溯)
}

// PA异常预测：样本条目预处理
export interface PaPreprocessedSampleRow {
    // 基础四列
    Serial: string;
    ProductName: string;
    Timestamp: string;
    SourceFile: string;

    // —— 数值特征 Numerical Features（合并/均值 + 直接数值）
    DpaVddSv: number | null;
    PaVddSv: number | null;

    'IDpaSv:.0': number | null;
    'IDpaSv:.1': number | null;
    'IDpaSv:.2': number | null;
    'IDpaSv:.3': number | null;

    'IMpaSv:.0': number | null;
    'IMpaSv:.1': number | null;
    'IMpaSv:.2': number | null;
    'IMpaSv:.3': number | null;

    LinAlarm: number | null;
    dpdNomPwr: number | null;
    dpdRestartCounter: number | null;
    powerClass: number | null;
    powerLevel: number | null;
    rfPower: number | null;
    torGainBackoff: number | null;
    torTemp: number | null;
    txAtt: number | null;
    txDpdGainDefault: number | null;
    txDpdPma: number | null;
    txPma: number | null;
    txPmb: number | null;
    txTorPmb: number | null;

    // —— 分类型特征 Categorical Features（字符/布尔）
    // 布尔（true/false），来自 bool_categorical_features
    autoPeakPhaseCal: boolean | null;
    delayEstimationEnable: boolean | null;
    dpGainLoopEnable: boolean | null;
    dpTsEnable: boolean | null;
    dpdAutoStart: boolean | null;
    gainAutoStart: boolean | null;
    ganBoostModeEnable: boolean | null;
    islastDelEstFracSuccess: boolean | null;
    shpAutoStart: boolean | null;
    shpGanAlgEnabled: boolean | null;
    shpGanAlgFunctionStatus: boolean | null;
    shpGanAlgHwCapablility: boolean | null;
    torSupported: boolean | null;

    // 字符（保留原始字符串），来自 categorical_features \ bool_categorical_features
    delayEst: string | null;
    desc: string | null;
    dpd: string | null;
    gainStateMachine: string | null;
    ganBoostModeState: string | null;
    linearizationStateMachine: string | null;
    runMode: string | null;
    status: string | null;
    statusBit: string | null;
    subId: string | null;
}

// 日志处理展示表格
export interface GeneratedRow {
    zipName: string;

    // 抽取
    xlsxName: string;               // *_extracted.xlsx
    xlsxHandle?: FileSystemFileHandle;
    xlsxUrl?: string;

    // 解析
    parsedJsonName?: string;        // *_extracted_parsed.json
    parsedJsonHandle?: FileSystemFileHandle;
    parsedJsonUrl?: string;

    parsedXlsxName?: string;        // *_extracted_parsed.xlsx
    parsedXlsxHandle?: FileSystemFileHandle;
    parsedXlsxUrl?: string;

    // 条目样本生成 - PA异常预测
    paSamplesJsonName?: string;       // <serial>_entry_sample_generated.json
    paSamplesJsonHandle?: FileSystemFileHandle;
    paSamplesJsonUrl?: string;

    paSamplesXlsxName?: string;       // <serial>_entry_sample_generated.xlsx
    paSamplesXlsxHandle?: FileSystemFileHandle;
    paSamplesXlsxUrl?: string;

    // 条目样本预处理 - PA异常预测
    paSamplesPreprocessJsonName?: string;      // <SN>_entry_sample_generated_preprocessed.json
    paSamplesPreprocessJsonHandle?: FileSystemFileHandle;
    paSamplesPreprocessJsonUrl?: string;

    paSamplesPreprocessXlsxName?: string;      // <SN>_entry_sample_generated_preprocessed.xlsx
    paSamplesPreprocessXlsxHandle?: FileSystemFileHandle;
    paSamplesPreprocessXlsxUrl?: string;

    dirLabel?: string;

    dirHandle?: FileSystemDirectoryHandle;  // 用于“同目录聚合”的目录句柄
}
