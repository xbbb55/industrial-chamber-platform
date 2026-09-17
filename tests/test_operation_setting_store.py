from decimal import Decimal

from device_edge.mysql_store import (
    CORRECTION_SETTING_COLUMNS,
    OPERATION_SETTING_COLUMNS,
    OTHER_SETTING_COLUMNS,
    SYSTEM_BASIC_SETTING_COLUMNS,
    OperationSettingStore,
)


def test_operation_setting_legacy_row_maps_json_field_names():
    row = tuple(Decimal(str(index + 1)) for index in range(len(OPERATION_SETTING_COLUMNS)))
    value = OperationSettingStore._as_value(row)

    assert value == {
        "airTEMP_H": 1.0,
        "airTEMP_L": 2.0,
        "dutTEMP_H": 3.0,
        "dutTEMP_L": 4.0,
        "dutModeAir_H": 5.0,
        "dutModeAir_L": 6.0,
    }


def test_operation_setting_full_row_preserves_named_other_fields():
    columns = (*OPERATION_SETTING_COLUMNS, *OTHER_SETTING_COLUMNS)
    row = tuple(range(len(columns)))
    value = OperationSettingStore._as_value(row, columns)

    assert value["dutControl"] == 6
    assert value["dutSel"] == 7
    assert value["DM9"] == 8
    assert value["waitTEMP"] == 9
    assert value["waitHUMI"] == 10
    assert value["event"] == 11
    assert value["powerRestoration"] == 12
    assert value["afterShutdow"] == 13


def test_system_basic_row_maps_database_column_names():
    row = tuple(Decimal(str(index + 1)) for index in range(len(SYSTEM_BASIC_SETTING_COLUMNS)))

    value = OperationSettingStore._as_value(row, SYSTEM_BASIC_SETTING_COLUMNS)

    assert value == {
        "TEMP_OP_H": 1.0,
        "TEMP_OP_L": 2.0,
        "HUMI_OP_H": 3.0,
        "HUMI_OP_L": 4.0,
        "HUMI_AirOP_H": 5.0,
        "HUMI_AirOP_L": 6.0,
        "heatingUpDownHz": 7.0,
        "constantTEMPHz": 8.0,
        "HumiHeatHz": 9.0,
        "otherHz": 10.0,
    }


def test_correction_row_maps_database_column_names():
    row = tuple(Decimal(str(index + 1)) for index in range(len(CORRECTION_SETTING_COLUMNS)))

    value = OperationSettingStore._as_value(row, CORRECTION_SETTING_COLUMNS)

    assert tuple(value) == CORRECTION_SETTING_COLUMNS
    assert value["TEMP_Area1"] == 1.0
    assert value["TEMP_Correction"] == 9.0
    assert value["HUMI_Area1"] == 10.0
    assert value["HUMI_Correction"] == 18.0
    assert value["DUT1_Collected"] == 19.0
    assert value["DUT1_Corrected"] == 20.0
    assert value["DUT1_Final"] == 21.0
    assert value["DUT10_Collected"] == 46.0
    assert value["DUT10_Corrected"] == 47.0
    assert value["DUT10_Final"] == 48.0
