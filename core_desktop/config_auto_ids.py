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
    "dd_list_database": "m_boxDatabase",
    "dd_list_server": "m_boxServer",
    "dd_list_authorization": "m_boxAuthorization",
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
    "cb_scheduled_reports": "m_chkSaveScheduledReports",
    "lk_save_and_apply": "m_lnkApply",

    # =========================================================================
    # TRBOnet Dispatch Console
    # =========================================================================
    "window_connect": "Connect to TRBOnet Server",
    "window_console": "TRBOnet Enterprise 6.5 / Dispatch Console",
    "btn_connect": "m_btnConnect",
    "title_bar": "TitleBar",
    "btn_close": "Close",
    "panel_voice_ip": "VoiceIPControlRadioLarge",
    "lbl_radio_name": "m_lblRadioName",
    "cbx_recipients": "m_cbxRecipients",
    "btn_ptt": "m_btnPTT",
    "dd_address": "m_tbServer",
    "field_port": "m_numPort",
    "dd_method": "m_boxAuthType",
    "field_username": "m_tbUser",
    "field_password": "m_tbPassword",
    "default_radio_interface": "m_pnlRadios",
    "vb_call_type": "m_tbCallType",
    "vb_call_info": "m_tbCallInfo",
    "vb_call_sender": "m_tbTransmitInfo",

    # =========================================================================
    # TRBOnet One
    # =========================================================================
    "window_connection_manager": "TRBOnet Connection Manager",
    "window_one": "TRBOnet One",
    "combo_console_type": "ConsoleTypeCb",
    "btn_connect_one": "btnConnect",
    "btn_ptt_one": "PTT",
    "cm_user_name_one": "TbLogin",
    "cm_password_one": "tbPassword",
    "cm_address_one": "TbIpAddress",
    "cm_port_one": "TbPort",
    "cm_auth_method_one": "IdentityCb",

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
    "test_db_connect_success": "configured successfully",
    "test_db_connect_inconsistent_version": "Inconsistent database version",
    "upgrade_db_success": "has been upgraded to the latest version",

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
    "console_ready": "TRBOnet Enterprise",
}

# ============================================================================
# НАЗВАНИЯ ПРОЦЕССОВ
# ============================================================================

PROCESS_NAMES = {
    "console": "TRBOnet.Console.exe",
    "one": "TRBOnet.One.exe",
    "server": "TRBOnet.Server.exe",
}

# ============================================================================
# СЛОВАРЬ ЦВЕТОВ
# ============================================================================

COLORS = {
    "GREEN": ["#D9F9C8", "#8ed047"],
    "RED": "#ff0000",
    "BLUE": ["#0000ff", "#0b8fe3", "#0b8fe2"],
    "YELLOW": "#ffff00",
    "ORANGE": "#ffa500",
    "WHITE": "#ffffff",
    "BLACK": "#000000",
    "GRAY": "#808080",
    "DARK_GRAY": "#404040",
    "LIGHT_GRAY": "#c0c0c0",
    "STATUS_OK": "#00cc00",
    "STATUS_ERROR": "#ff3333",
    "STATUS_WARNING": "#ffaa00",
    "STATUS_DISABLED": "#999999",
    # Можно добавлять свои цвета в любом формате
    "CUSTOM_RGB": (255, 128, 0),  # RGB кортеж
    "CUSTOM_HEX": "#ff8000",
}