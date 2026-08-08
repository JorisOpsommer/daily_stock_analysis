# Graph Report - apps  (2026-08-08)

## Corpus Check
- 296 files · ~415,653 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2313 nodes · 5329 edges · 109 communities (98 shown, 11 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 86 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e730bfe8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]

## God Nodes (most connected - your core abstractions)
1. `useUiLanguage()` - 114 edges
2. `cn()` - 89 edges
3. `t()` - 85 edges
4. `ParsedApiError` - 34 edges
5. `normalizeReportLanguage()` - 34 edges
6. `getParsedApiError()` - 32 edges
7. `Badge()` - 32 edges
8. `Button()` - 32 edges
9. `ReportLanguage` - 28 edges
10. `getReportText()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `getOutcomeLabel()` --calls--> `t()`  [INFERRED]
  dsa-web/src/components/decision-signals/DecisionSignalDisplay.tsx → dsa-web/src/utils/__tests__/decisionSignalLabels.test.ts
- `ReportOverview()` --calls--> `formatChangePct()`  [INFERRED]
  dsa-web/src/components/report/ReportOverview.tsx → dsa-web/src/components/history/StockHistoryTrendDrawer.tsx
- `ReportOverview()` --calls--> `getPriceChangeStyle()`  [INFERRED]
  dsa-web/src/components/report/ReportOverview.tsx → dsa-web/src/components/history/StockHistoryTrendDrawer.tsx
- `getEdgeLabel()` --calls--> `t()`  [INFERRED]
  dsa-web/src/components/run-flow/RunFlowGraph.tsx → dsa-web/src/utils/__tests__/decisionSignalLabels.test.ts
- `getSetupCheckStatusLabel()` --calls--> `t()`  [INFERRED]
  dsa-web/src/pages/SettingsPage.tsx → dsa-web/src/utils/__tests__/decisionSignalLabels.test.ts

## Import Cycles
- None detected.

## Communities (109 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (86): { app, BrowserWindow, dialog, ipcMain, shell, nativeTheme }, appRootDev, backupPackagedRuntimeState(), broadcastDesktopUpdateState(), buildBackendArgs(), buildBackendEnvironment(), buildBackendUrl(), buildElectronUpdaterState() (+78 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (66): Badge(), ScrollArea(), DashboardPanelHeader(), DashboardPanelHeaderProps, DashboardStateBlock(), DashboardStateBlockProps, HistoryList(), HistoryListProps (+58 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (60): FallbackInput(), StockAutocomplete(), StockAutocompleteBoundary, StockAutocompleteBoundaryProps, StockAutocompleteBoundaryState, StockAutocompleteInner(), StockAutocompleteProps, MARKET_BADGE_CONFIG (+52 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (48): Card(), GaugeVisualStyle, ScoreGauge(), ScoreGaugeProps, SentimentKey, MarketReviewReportView(), ReportDetails(), ReportDetailsProps (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (53): BadgeVariant, itemList(), MarketStructureCard(), MarketStructureCardProps, MetricLineProps, RISK_TAG_TEXT, STATUS_VARIANT, TEXT (+45 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (38): AppPage(), AppPageProps, BadgeProps, BadgeVariant, glowStyles, variantStyles, CardProps, Checkbox() (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (42): ACTION_VALUES, BreakdownMode, HORIZON_VALUES, PROFILE_OPTIONS, Props, calibration, DecisionAction, MarketPhaseValue (+34 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (36): SystemConfigValidationError, {
  getGenerationBackendStatus,
  previewGenerationBackendStatus,
  testGenerationBackend,
}, litellmStatus, localCliStatus, smokePassed, AgentBackendStatusPreviewRequest, DiscoverLLMChannelModelsRequest, DiscoverLLMChannelModelsResponse (+28 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (41): ACTION_VARIANTS, asJsonViewerData(), BadgeVariant, DecisionSignalCard(), DecisionSignalCardProps, DecisionSignalDetails(), DecisionSignalDetailsProps, DetailRowProps (+33 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (27): AlertRuleForm(), { getAccounts }, items, report, MarketReviewRegionSelectorProps, testNotificationChannel, fallbackContext, UiLanguageContext (+19 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (33): analysisApi, GetHistoryListParams, historyApi, post, BadgeVariant, compactId(), COMPONENT_ORDER, COMPONENT_STATUS_STYLE (+25 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (32): DuplicateTaskError, useWatchlist(), HomePage(), buildHistoryParams(), buildMarketReviewHistoryParams(), buildStockHistoryParams(), CompletedTaskSelectionIntent, consumeCompletedTaskSelection() (+24 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (36): CashListQuery, CorporateListQuery, EventQuery, FxRefreshQuery, portfolioApi, SnapshotQuery, TradeListQuery, DecisionSignalItem (+28 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (28): ConfirmDialog(), ConfirmDialogProps, UiLanguageToggle(), UiLanguageToggleProps, UiLanguageToggleVariant, Shell(), ShellProps, ShellHeaderProps (+20 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (35): ACTION_OPTIONS, AppliedTimelineContext, buildNextTimelineFilters(), DEFAULT_LIST_FILTERS, DEFAULT_TIMELINE_FILTERS, formatStatNumber(), formatStatPercent(), getCandidateKey() (+27 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (29): areModelsEquivalent(), buildLlmFailureText(), CAPABILITY_STATUS_LABELS, CHANNEL_FIELD_SUFFIXES, ChannelDiscoveryState, ChannelTestState, FALSEY_VALUES, getLlmErrorCodeLabel() (+21 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (33): CHANGE_DIRECTION_OPTIONS, CROSS_DIRECTION_OPTIONS, MARKET_ALERT_TYPE_OPTIONS, MARKET_LIGHT_STATUS_OPTIONS, PORTFOLIO_ALERT_TYPE_OPTIONS, PRICE_DIRECTION_OPTIONS, SEVERITY_OPTIONS, STOP_LOSS_MODE_OPTIONS (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (30): SettingsLoading(), AGENT_BACKEND_STATUS_KEYS, DesktopUpdateNotice, DesktopUpdateState, DesktopWindow, FirstRunSetupCard(), FirstRunSetupCardProps, formatSchedulerTimestamp() (+22 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (34): build, afterPack, appId, directories, extraResources, files, mac, nsis (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (22): HomeWorkspaceTab, WatchlistAnalyzeMode, defaultMocks, useDashboardLifecycle(), UseDashboardLifecycleOptions, useHomeDashboardState(), useTaskStream(), BatchAnalyzeStatus (+14 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (23): backtestApi, BACKTEST_DIRECTION_EXPECTED_LABELS, BACKTEST_MOVEMENT_LABELS, BACKTEST_OUTCOME_LABELS, BACKTEST_PHASE_FILTER_OPTIONS, BACKTEST_PHASE_LABELS, BACKTEST_STATUS_LABELS, BACKTEST_TEXT (+15 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (28): StatusDot(), EventFilter, eventText(), FILTER_ICONS, matchesFilter(), RunFlowEventList(), RunFlowEventListProps, RunFlowSummaryBar() (+20 more)

### Community 22 - "Community 22"
Cohesion: 0.09
Nodes (27): coerceFiniteNumber(), CopyType, formatMarketAmount(), formatMarketCount(), formatMarketHighLow(), formatMarketNumber(), formatMarketPercent(), getPayloadSections() (+19 more)

### Community 23 - "Community 23"
Cohesion: 0.11
Nodes (28): AppContent(), ApiErrorAlert(), Drawer(), DrawerProps, JsonViewer(), Loading(), LoadingProps, Select() (+20 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (20): buildDataSourceBlocks(), compareLaneNodes(), dataTypeFromNode(), EdgeFocusLevel, EdgePort, getEdgeLabel(), isExpandableNode(), isExpandedProviderGroup() (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (24): alertsApi, omitUndefined(), toSnakeRulePayload(), { get, post, deleteRequest }, AlertRuleFormProps, AlertDeleteResponse, AlertDirection, AlertDryRunStatus (+16 more)

### Community 26 - "Community 26"
Cohesion: 0.12
Nodes (24): decisionSignalsApi, getDecisionSignalReassessBlockedError(), omitUndefined(), toDecisionSignalFeedbackItem(), toDecisionSignalItem(), toDecisionSignalListResponse(), toDecisionSignalMutationResponse(), toDecisionSignalOutcomeItem() (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (24): ParsedApiError, ApiErrorAlertProps, StockHistoryTrendDrawerProps, AnalysisContextSummary(), BadgeVariant, BLOCK_LABELS, MISSING_REASON_LABELS, STATUS_FALLBACK_GUIDANCE (+16 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (20): AlertRuleBusyState, AlertRuleEnabledFilter, AlertTypeFilter, AlertTriggerHistory(), AlertTriggerHistoryProps, renderPhaseQuality(), statusLabel, EmptyState() (+12 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (28): PortfolioPage(), PortfolioCashDirection, PortfolioCorporateActionType, PortfolioFxRefreshResponse, PortfolioImportCommitResponse, PortfolioImportParseResponse, PortfolioPositionItem, PortfolioSide (+20 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (19): isParsedApiError(), Button(), Input(), AuthSettingsCard(), createNextModeLabel(), ChangePasswordCard(), getChannelOptions(), NotificationTestPanel() (+11 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (21): formatDateTime(), DecisionSignalTimelineProps, finiteNumber(), formatConfidence(), formatDateTime(), formatNumber(), LOCALE_BY_LANGUAGE, RANK_LABELS (+13 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (20): inferPasswordIconType(), isMultiValueField(), normalizeSelectOptions(), parseMultiValues(), renderFieldControl(), resolveDisplayValue(), SettingsField(), SettingsFieldProps (+12 more)

### Community 33 - "Community 33"
Cohesion: 0.08
Nodes (7): formatRecoverableScreenTaskPollingError(), getScreenMessages(), HOTSPOT_ICON_RULES, KNOWN_SNAPSHOT_SOURCES, MARKETS, PersistedScreenTask, toMessageList()

### Community 34 - "Community 34"
Cohesion: 0.17
Nodes (23): ApiErrorCategory, attachParsedApiError(), buildMatchText(), createApiError(), CreateParsedApiErrorOptions, ErrorCarrier, extractErrorCode(), extractErrorPayloadText() (+15 more)

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (21): ACTIVE_NODE_STATUSES, appendDerivedEdge(), appendEdge(), buildLiveSummary(), dataTypeFromEvent(), dataTypeFromNode(), edgeExists(), eventNodeId() (+13 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (19): baseSnapshot, buildProviderGroupNode(), buildRunFlowTopologyModel(), compactProviderChain(), contextBlockKeyFromNode(), countByStatus(), dataTypeFromNode(), firstDefinedRecordCount() (+11 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (23): compilerOptions, allowImportingTsExtensions, allowSyntheticDefaultImports, erasableSyntaxOnly, esModuleInterop, jsx, lib, module (+15 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (17): AlertRuleBusyAction, AlertRuleList(), AlertRuleListProps, formatParameters(), formatTarget(), rules, formatUiText(), ALERT_DIRECTION_LABELS (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (16): emptyFeedback, formattedCreatedAt, outcomeList, outcomeStats, persistableReassessResponse, persistedReassessItem, persistedReassessResponse, reassessResponse (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (22): devDependencies, babel-plugin-react-compiler, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, jsdom (+14 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (15): appRevision, buildInputDirectories, buildInputFiles, buildTime, getVendorChunkName(), getVendorPackageName(), gitDescription, packageJson (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.11
Nodes (17): AlertsPage, BacktestPage, ChatPage, DecisionSignalsPage, HomePage, LoginPage, NotFoundPage, PortfolioPage (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.13
Nodes (16): SettingsCategoryNavProps, { getConfig, validate, update }, sampleConfig, sampleLlmConfig, CATEGORY_DISPLAY_ORDER, isMultiValueSchema(), normalizeFieldValue(), RetryAction (+8 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (18): alphasiftApi, AlphaSiftCandidate, AlphaSiftHotspot, AlphaSiftHotspotDetail, AlphaSiftHotspotRouteItem, AlphaSiftHotspotsResponse, AlphaSiftHotspotStock, AlphaSiftInstallResponse (+10 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (13): authApi, AuthStatusResponse, apiClient, ExtractFromImageResponse, ExtractItem, stocksApi, SystemConfigConflictError, IMG_EXT (+5 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (17): get, usageApi, UsageCallRecord, UsageCallTypeBreakdown, UsageDashboard, UsageModelBreakdown, UsagePeriod, buildParsedError() (+9 more)

### Community 47 - "Community 47"
Cohesion: 0.15
Nodes (16): baseSignal, DecisionSignalStatus, ACTION_RANK, ActionFamily, buildTimelineData(), clamp(), finiteNumber(), getActionFamily() (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (16): AccountOption, DECISION_SIGNAL_MARKETS, EventType, FALLBACK_BROKERS, FlatPosition, FxRefreshContext, getSignalTime(), isNewerSignal() (+8 more)

### Community 49 - "Community 49"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (11): InlineAlert(), InlineAlertProps, InlineAlertVariant, variantStyles, getSafeErrorSummary(), sanitizeUrlLikeText(), SettingsPanelErrorBoundary(), SettingsPanelErrorBoundaryImpl (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (13): {
  analyzeAsync,
  exportEnv,
  getSchedulerStatus,
  getSetupStatus,
  importEnv,
  runSchedulerNow,
  updateSystemConfig,
  alphasiftEnable,
  alphasiftInstall,
  notifyAlphaSiftConfigChanged,
  notifySystemConfigChanged,
  desktopCheckForUpdates,
  desktopGetUpdateState,
  desktopInstallDownloadedUpdate,
  desktopOnUpdateStateChange,
  desktopOpenReleasePage,
  load,
  clearToast,
  setActiveCategory,
  save,
  resetDraft,
  setDraftValue,
  applyPartialUpdate,
  getChangedItems,
  refreshAfterExternalSave,
  refreshStatus,
  settingsPanelErrorBoundary,
  useAuthMock,
  useSystemConfigMock,
  webBuildInfoMock,
}, baseCategories, ConfigOverride, ConfigState, mockedAnchorClick, SetupStatusResponse, configuredApiBaseUrl, createBuildIdentifier() (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (17): dependencies, axios, camelcase-keys, clsx, lucide-react, motion, next-themes, react (+9 more)

### Community 53 - "Community 53"
Cohesion: 0.17
Nodes (13): DataSourceBlock, RunFlowGraphProps, RunFlowNodeDetailsProps, edges, heightFor(), lanes, nodes, positionedStyleFor() (+5 more)

### Community 54 - "Community 54"
Cohesion: 0.18
Nodes (11): ALWAYS_HIDDEN_METADATA_KEYS, DataQualityMetadata, DetailItem, DetailRow, isContextPackNode(), readDataQuality(), readDetailItems(), readNumberRecord() (+3 more)

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (11): AgentBackendStatusPanel(), AgentBackendStatusPanelProps, backendLabel(), statusMessage(), GenerationBackendStatusPanelProps, NotificationTestPanelProps, codexStatus, { getStatus, previewStatus } (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (12): TaskItem(), TaskItemProps, TaskPanel(), TaskPanelProps, baseTask, SSEEvent, AnalysisPhase, TaskInfo (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.17
Nodes (13): clearSharedReconnect(), closeSharedConnection(), connectSharedStream(), notifyConnectionState(), ParsedTaskStreamPayload, parseEventData(), reconnectSharedStream(), SSEEventType (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (13): agentApi, AgentStatusResponse, CancelChatStreamResponse, ChatRequest, ChatResponse, ChatSessionMessage, ChatStreamOptions, ChatStreamRequest (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (12): ChatSessionItem, getParsedApiError(), loadPortfolioSignalLookup(), AgentChatState, getFirstMeaningfulStreamError(), getInitialSessionId(), getStreamFailureError(), StreamAcceptedEvent (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (14): SystemConfigCategory, categoryDescriptionMap, categoryTitleMap, fieldDescriptionMap, fieldOptionLabelMap, fieldOptionLabelMapEn, fieldTitleMap, getCategoryDescription() (+6 more)

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (9): createParsedApiError(), AuthState, { chatPageShouldThrow, setCurrentRoute, useAgentChatStoreMock }, AuthContext, AuthContextValue, AuthProvider(), extractLoginError(), { getStatus, login, changePassword, logout, resetDashboardState } (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.20
Nodes (13): isCompareStockMessage(), resolveActiveStockContextFromMessage(), resolveUniqueStockNameContext(), restoreActiveStockContextFromMessages(), getStockCodeKey(), toPositionSignalLookupKey(), CONTEXTUAL_INDICATOR_TOKENS, EXCHANGE_PREFIXES (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (3): hasLocalStorage, IntersectionObserverMock, MemoryStorageMock

### Community 64 - "Community 64"
Cohesion: 0.20
Nodes (11): buildChatFollowUpContext(), buildFollowUpPrompt(), ChatFollowUpContext, convertMarketStructureToSnakeCase(), getMarketStructureContextForAgent(), hasInvalidFollowUpNameCharacter(), parseFollowUpRecordId(), resolveChatFollowUpContext() (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.26
Nodes (11): ChannelConfig, ChannelRow(), ChannelProtocol, getProviderTemplate(), isKnownProviderTemplate(), LLM_PROVIDER_CAPABILITY_LABELS, LLM_PROVIDER_TEMPLATE_BY_ID, LLM_PROVIDER_TEMPLATES (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.23
Nodes (10): ActiveStockContext, ActiveStockResolution, getMessageSkillLabel(), getMessageSkillNames(), getStageDoneLabel(), isStageDoneSuccessful(), QUICK_QUESTIONS, Message (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.26
Nodes (11): buildRealComponentFixture(), context, currentDir, isHttpUrl(), isMissingPlaywrightBrowser(), renderMarketStructureCard(), sourceRoot, startStaticServer() (+3 more)

### Community 68 - "Community 68"
Cohesion: 0.17
Nodes (10): mockClearCompletionBadge, {
  mockGetSkills,
  mockGetStatus,
  mockDeleteChatSession,
  mockSendChat,
  mockGetSystemConfig,
  mockUpdateSystemConfig,
  mockGetWatchlist,
  mockAddToWatchlist,
  mockRemoveFromWatchlist,
  mockDownloadSession,
  mockFormatSessionAsMarkdown,
  mockStockIndex,
}, mockLoadInitialSession, mockLoadSessions, mockStartNewChat, mockStartStream, mockStopStream, mockStoreState (+2 more)

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (11): buildRouteProvenanceMap(), hasRuntimeOnlyMaskedHermesSecret(), isHermesChannel(), normalizeAgentPrimaryModel(), parseRuntimeConfigFromItems(), resolveChannelRouteModels(), resolveModelPreview(), resolveTemperatureFromItems() (+3 more)

### Community 70 - "Community 70"
Cohesion: 0.33
Nodes (7): {
  mockGetWatchlist,
  mockAddToWatchlist,
  mockRemoveFromWatchlist,
}, UseWatchlistReturn, itemMatchesStockContext(), areStockCodesEquivalent(), findMatchingStockCode(), includesStockCode(), stockCodeMatchKey()

### Community 72 - "Community 72"
Cohesion: 0.20
Nodes (7): assert, { EventEmitter }, fs, Module, os, path, test

### Community 73 - "Community 73"
Cohesion: 0.22
Nodes (9): buildChangedItemKeys(), buildChannelDraftItems(), buildFilteredChannelUpdateItems(), channelNamesAreSafe(), channelsToUpdateItems(), isChannelSecretFieldKey(), parseChannelFieldKeys(), resolveInitialChannelApiKeySource() (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.31
Nodes (6): CodeExamples(), FOCUSABLE_SELECTOR, hasItems(), HelpList(), SettingsHelpButtonProps, SystemConfigFieldSchema

### Community 75 - "Community 75"
Cohesion: 0.25
Nodes (4): { contextBridge, ipcRenderer }, assert, Module, test

### Community 76 - "Community 76"
Cohesion: 0.25
Nodes (7): engines, node, npm, name, private, type, version

### Community 77 - "Community 77"
Cohesion: 0.29
Nodes (8): getRouteProvenance(), getRuntimeProvider(), hasCanonicalRouteAliasMismatch(), hasLegacyRuntimeSource(), isRuntimeModelAvailable(), routeIdentityCandidates(), sanitizeRuntimeConfigForSave(), usesDirectEnvProvider()

### Community 78 - "Community 78"
Cohesion: 0.29
Nodes (7): scripts, build, dev, lint, preview, test, test:smoke

### Community 79 - "Community 79"
Cohesion: 0.29
Nodes (3): Particle, PARTICLE_COLORS, ParticleBackground()

### Community 80 - "Community 80"
Cohesion: 0.38
Nodes (6): RunFlowPanel(), RunFlowPanelProps, isUsableSource(), useRunFlowSnapshot(), UseRunFlowSnapshotOptions, RunFlowSnapshotSource

### Community 81 - "Community 81"
Cohesion: 0.33
Nodes (7): formatHotspotEmptyMessage(), formatScreenMessage(), formatScreenTaskFailure(), normalizeScreenMessageKey(), parseSourceDiagnostic(), summarizeAlphaSiftDiagnostic(), truncateMessageDetail()

### Community 82 - "Community 82"
Cohesion: 0.29
Nodes (7): formatHotspotMetric(), formatHotspotUpdatedAt(), formatNumber(), formatPercent(), formatStockChangeText(), getHotspotRouteItems(), StockScreeningPage()

### Community 83 - "Community 83"
Cohesion: 0.52
Nodes (5): isObviouslyInvalidStockQuery(), looksLikeStockCode(), STOCK_CODE_PATTERNS, validateStockCode(), ValidationResult

### Community 84 - "Community 84"
Cohesion: 0.40
Nodes (3): EyeToggleIcon(), EyeToggleIconProps, InputProps

### Community 85 - "Community 85"
Cohesion: 0.33
Nodes (3): buildModelOptions(), LLMChannelEditor(), {
  update,
  testLLMChannel,
  discoverLLMChannelModels,
}

### Community 86 - "Community 86"
Cohesion: 0.40
Nodes (4): createEventSourceInstance(), { getTaskStreamUrl }, MockEventSource, MockEventSourceInstance

### Community 89 - "Community 89"
Cohesion: 0.40
Nodes (3): BUTTON_SIZE_STYLES, BUTTON_VARIANT_STYLES, ButtonProps

### Community 94 - "Community 94"
Cohesion: 0.50
Nodes (3): systemConfigApi, get, post

### Community 95 - "Community 95"
Cohesion: 0.67
Nodes (3): getTokenClassName(), JsonViewerProps, renderHighlightedLine()

### Community 96 - "Community 96"
Cohesion: 0.50
Nodes (4): ChannelCapabilityState, ChannelRowProps, LLMCapabilityCheck, LLMCapabilityCheckResult

### Community 101 - "Community 101"
Cohesion: 0.67
Nodes (3): buildLlmTestHint(), getFirstCapabilityHint(), getLlmTroubleshootingHint()

## Knowledge Gaps
- **733 isolated node(s):** `{ app, BrowserWindow, dialog, ipcMain, shell, nativeTheme }`, `path`, `fs`, `{ spawn }`, `net` (+728 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUiLanguage()` connect `Community 23` to `Community 1`, `Community 3`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 11`, `Community 13`, `Community 14`, `Community 16`, `Community 17`, `Community 19`, `Community 20`, `Community 21`, `Community 24`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 38`, `Community 42`, `Community 45`, `Community 46`, `Community 48`, `Community 50`, `Community 54`, `Community 55`, `Community 56`, `Community 66`, `Community 74`, `Community 80`, `Community 84`, `Community 89`, `Community 95`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `getParsedApiError()` connect `Community 59` to `Community 3`, `Community 7`, `Community 11`, `Community 14`, `Community 15`, `Community 17`, `Community 19`, `Community 20`, `Community 23`, `Community 28`, `Community 30`, `Community 33`, `Community 34`, `Community 35`, `Community 43`, `Community 45`, `Community 48`, `Community 55`, `Community 61`, `Community 66`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `ParsedApiError` connect `Community 27` to `Community 3`, `Community 7`, `Community 10`, `Community 11`, `Community 14`, `Community 15`, `Community 17`, `Community 19`, `Community 20`, `Community 23`, `Community 28`, `Community 30`, `Community 33`, `Community 34`, `Community 35`, `Community 43`, `Community 45`, `Community 46`, `Community 48`, `Community 55`, `Community 59`, `Community 61`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `t()` (e.g. with `AppContent()` and `ApiErrorAlert()`) actually correct?**
  _`t()` has 84 INFERRED edges - model-reasoned connections that need verification._
- **What connects `{ app, BrowserWindow, dialog, ipcMain, shell, nativeTheme }`, `path`, `fs` to the rest of the system?**
  _733 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05329593267882188 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05554035567715458 - nodes in this community are weakly interconnected._