"""
Конфигурация AutomationId и текстов для TRBOnet
"""

# ============================================================================
# AUTOMATION ID ДЛЯ TRBONET (все приложения)
# ============================================================================

AUTO_IDS = {
    # =========================================================================
    # TRBOnet Server
    # =========================================================================
    "tree": "m_tree",
    "tab_database": "Database",
    "tab_service": "Service",
    "panel_database": "ConfigControlDatabase",
    "panel_data": "m_pnlData",
    "panel_tree": "m_pnlTree",
    "btn_create_database": "m_btnCreate",
    "btn_upgrade_database": "m_btnUpdate",
    "btn_test_connection": "m_btnTest",
    "combo_database": "m_boxDatabase",
    "combo_server": "m_boxServer",
    "combo_authorization": "m_boxAuthorization",
    "lbl_database": "m_lblDatabase",
    "lbl_server": "m_lblServer",
    "lbl_authorization": "m_lblAuthorization",
    "edit_login": "m_boxLogin",
    "edit_password": "m_boxPassword",
    "btn_install_service": "m_btnInstall",
    "btn_uninstall_service": "m_btnUninstall",
    "btn_start_service": "m_btnAction",
    "btn_apply": "m_btnApply",
    "btn_ok": "m_btnOk",
    "btn_cancel": "m_btnCancel",
    "btn_defaults": "m_btnDefaults",

    # =========================================================================
    # TRBOnet Dispatch Console
    # =========================================================================
    "window_connect": "Connect to TRBOnet Server",
    "window_console": "TRBOnet Enterprise /Dispatch Console",
    "btn_connect": "m_btnConnect",
    "title_bar": "TitleBar",
    "btn_close": "Close",
    "panel_voice_ip": "VoiceIPControlRadioLarge",
    "lbl_radio_name": "m_lblRadioName",
    "cbx_recipients": "m_cbxRecipients",
    "btn_ptt": "m_btnPTT",

    # =========================================================================
    # TRBOnet One
    # =========================================================================
    "window_connection_manager": "TRBOnet Connection Manager",
    "window_one": "TRBOnet One",
    "combo_console_type": "ConsoleTypeCb",
    "btn_connect_one": "btnConnect",
    "btn_ptt_one": "PTT",
}

# ============================================================================
# ОЖИДАЕМЫЕ ТЕКСТЫ
# ============================================================================

DIALOG_TEXTS = {
    # Server
    "creation_dialog": "has been created",
    "restart_dialog": "Do you want to restart the server?",
    "service_started": "Service started",
    "service_stopped": "Service stopped",

    # Dispatch Console
    "intercom": "Intercom",
    "all_call": "All Call",

    # TRBOnet One
    "connection_manager": "TRBOnet Connection Manager",
    "one_window": "TRBOnet One",
    "console_type_one": "TRBOnetOne",
}

# ============================================================================
# ОЖИДАЕМЫЕ ТЕКСТЫ ДЛЯ ПРОВЕРКИ ГОТОВНОСТИ ОКНА
# ============================================================================

READY_TEXTS = {
    "connection_manager_ready": "TRBOnet Connection Manager",
    "one_ready": "TRBOnet One",
}

# ============================================================================
# НАЗВАНИЯ ПРОЦЕССОВ
# ============================================================================

PROCESS_NAMES = {
    "console": "TRBOnet.Console.exe",
    "one": "TRBOnet.One.exe",
}