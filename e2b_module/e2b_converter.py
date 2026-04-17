"""
E2B R3 ICSR Import/Export Module
=================================
Модуль импорта и экспорта данных по безопасности лекарственных препаратов
в формате E2B R3 (ICH E2B(R3) Individual Case Safety Report).

Поддерживаемые форматы конвертации:
    XML (E2B R3) → JSON
    XML (E2B R3) → HTML
    XML (E2B R3) → SQL
    JSON          → XML (E2B R3)

Использование:
    from e2b_converter import E2BConverter

    with open('report.xml', encoding='utf-8') as f:
        xml_data = f.read()

    converter = E2BConverter()
    json_out = converter.xml_to_json(xml_data)
    html_out = converter.xml_to_html(xml_data)
    sql_out  = converter.xml_to_sql(xml_data)

Стандарт: ICH E2B(R3)
Лицензия: GNU GPL v3
"""

import json
import re
import xml.etree.ElementTree as ET
from html import escape as he
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

__version__ = '1.0.0'
__author__ = 'E2B4Free Project'
__license__ = 'GPL-3.0'

# ---------------------------------------------------------------------------
# Field labels  (E2B code → human-readable English)
# ---------------------------------------------------------------------------

FIELD_LABELS: Dict[str, str] = {
    'c_1_identification_case_safety_report': 'C.1 Identification of the Case Safety Report',
    'c_1_1_sender_safety_report_unique_id': 'C.1.1 Sender Safety Report Unique ID',
    'c_1_2_date_creation': 'C.1.2 Date of Creation',
    'c_1_3_type_report': 'C.1.3 Type of Report',
    'c_1_4_date_report_first_received_source': 'C.1.4 Date Report First Received from Source',
    'c_1_5_date_most_recent_information': 'C.1.5 Date of Most Recent Information',
    'c_1_6_1_additional_documents_available': 'C.1.6.1 Additional Documents Available',
    'c_1_6_1_r_documents_held_sender': 'C.1.6.1(R) Documents Held by Sender',
    'c_1_6_1_r_1_documents_held_sender': 'C.1.6.1(R).1 Documents Held by Sender',
    'c_1_7_fulfil_local_criteria_expedited_report': 'C.1.7 Fulfil Local Criteria for Expedited Report',
    'c_1_8_1_worldwide_unique_case_identification_number': 'C.1.8.1 Worldwide Unique Case Identification Number',
    'c_1_8_2_first_sender': 'C.1.8.2 First Sender',
    'c_1_9_1_other_case_ids_previous_transmissions': 'C.1.9.1 Other Case IDs — Previous Transmissions',
    'c_1_9_1_r_source_case_id': 'C.1.9.1(R) Source Case ID',
    'c_1_9_1_r_1_source_case_id': 'C.1.9.1(R).1 Source Case ID',
    'c_1_9_1_r_2_case_id': 'C.1.9.1(R).2 Case ID',
    'c_1_10_r_identification_number_report_linked': 'C.1.10(R) Identification Number of Report Linked',
    'c_1_11_1_report_nullification_amendment': 'C.1.11.1 Report Nullification / Amendment',
    'c_1_11_2_reason_nullification_amendment': 'C.1.11.2 Reason for Nullification / Amendment',
    'c_2_r_primary_source_information': 'C.2(R) Primary Source Information',
    'c_2_r_1_1_reporter_title': 'C.2.r.1.1 Reporter Title',
    'c_2_r_1_2_reporter_given_name': 'C.2.r.1.2 Reporter Given Name',
    'c_2_r_1_3_reporter_middle_name': 'C.2.r.1.3 Reporter Middle Name',
    'c_2_r_1_4_reporter_family_name': 'C.2.r.1.4 Reporter Family Name',
    'c_2_r_2_1_reporter_organisation': 'C.2.r.2.1 Reporter Organisation',
    'c_2_r_2_2_reporter_department': 'C.2.r.2.2 Reporter Department',
    'c_2_r_2_3_reporter_street': 'C.2.r.2.3 Reporter Street',
    'c_2_r_2_4_reporter_city': 'C.2.r.2.4 Reporter City',
    'c_2_r_2_5_reporter_state_province': 'C.2.r.2.5 Reporter State/Province',
    'c_2_r_2_6_reporter_postcode': 'C.2.r.2.6 Reporter Postcode',
    'c_2_r_2_7_reporter_telephone': 'C.2.r.2.7 Reporter Telephone',
    'c_2_r_3_reporter_country_code': 'C.2.r.3 Reporter Country Code',
    'c_2_r_4_qualification': 'C.2.r.4 Qualification',
    'c_2_r_5_primary_source_regulatory_purposes': 'C.2.r.5 Primary Source for Regulatory Purposes',
    'c_3_information_sender_case_safety_report': 'C.3 Information Sender of Case Safety Report',
    'c_3_1_sender_type': 'C.3.1 Sender Type',
    'c_3_2_sender_organisation': 'C.3.2 Sender Organisation',
    'c_3_3_1_sender_department': 'C.3.3.1 Sender Department',
    'c_3_3_2_sender_title': 'C.3.3.2 Sender Title',
    'c_3_3_3_sender_given_name': 'C.3.3.3 Sender Given Name',
    'c_3_3_4_sender_middle_name': 'C.3.3.4 Sender Middle Name',
    'c_3_3_5_sender_family_name': 'C.3.3.5 Sender Family Name',
    'c_3_4_1_sender_street_address': 'C.3.4.1 Sender Street Address',
    'c_3_4_2_sender_city': 'C.3.4.2 Sender City',
    'c_3_4_3_sender_state_province': 'C.3.4.3 Sender State/Province',
    'c_3_4_4_sender_postcode': 'C.3.4.4 Sender Postcode',
    'c_3_4_5_sender_country_code': 'C.3.4.5 Sender Country Code',
    'c_3_4_6_sender_telephone': 'C.3.4.6 Sender Telephone',
    'c_3_4_7_sender_fax': 'C.3.4.7 Sender Fax',
    'c_3_4_8_sender_email': 'C.3.4.8 Sender Email',
    'c_4_r_literature_reference': 'C.4(R) Literature Reference',
    'c_4_r_1_literature_reference': 'C.4.r.1 Literature Reference',
    'c_5_study_identification': 'C.5 Study Identification',
    'c_5_1_r_study_registration': 'C.5.1(R) Study Registration',
    'c_5_1_r_1_study_registration_number': 'C.5.1.r.1 Study Registration Number',
    'c_5_1_r_2_study_registration_country': 'C.5.1.r.2 Study Registration Country',
    'c_5_2_study_name': 'C.5.2 Study Name',
    'c_5_3_sponsor_study_number': 'C.5.3 Sponsor Study Number',
    'c_5_4_study_type_reaction': 'C.5.4 Study Type Where Reaction(s)/Event(s) Were Observed',
    'd_patient_characteristics': 'D Patient Characteristics',
    'd_1_patient': 'D.1 Patient (name or initials)',
    'd_1_1_1_medical_record_number_source_gp': 'D.1.1.1 Medical Record Number (GP)',
    'd_1_1_2_medical_record_number_source_specialist': 'D.1.1.2 Medical Record Number (Specialist)',
    'd_1_1_3_medical_record_number_source_hospital': 'D.1.1.3 Medical Record Number (Hospital)',
    'd_1_1_4_medical_record_number_source_investigation': 'D.1.1.4 Medical Record Number (Investigation)',
    'd_2_1_date_birth': 'D.2.1 Date of Birth',
    'd_2_2a_age_onset_reaction_num': 'D.2.2a Age at Time of Onset (Number)',
    'd_2_2b_age_onset_reaction_unit': 'D.2.2b Age Unit',
    'd_2_2_1a_gestation_period_reaction_foetus_num': 'D.2.2.1a Gestation Period (Number)',
    'd_2_2_1b_gestation_period_reaction_foetus_unit': 'D.2.2.1b Gestation Period Unit',
    'd_2_3_patient_age_group': 'D.2.3 Patient Age Group',
    'd_3_body_weight': 'D.3 Body Weight (kg)',
    'd_4_height': 'D.4 Height (cm)',
    'd_5_sex': 'D.5 Sex',
    'd_6_last_menstrual_period_date': 'D.6 Last Menstrual Period Date',
    'd_7_1_r_structured_information_medical_history': 'D.7.1(R) Structured Medical History',
    'd_7_2_text_medical_history': 'D.7.2 Text for Relevant Medical History',
    'd_7_3_concomitant_therapies': 'D.7.3 Concomitant Therapies',
    'd_8_r_past_drug_history': 'D.8(R) Relevant Past Drug History',
    'd_9_1_date_death': 'D.9.1 Date of Death',
    'd_9_2_r_cause_death': 'D.9.2(R) Cause of Death',
    'd_9_3_autopsy': 'D.9.3 Was Autopsy Done?',
    'd_9_4_r_autopsy_determined_cause_death': 'D.9.4(R) Autopsy Determined Cause(s) of Death',
    'd_10_1_parent_identification': 'D.10.1 Parent Identification',
    'd_10_2_1_date_birth_parent': 'D.10.2.1 Date of Birth of Parent',
    'd_10_2_2a_age_parent_num': 'D.10.2.2a Age of Parent (Number)',
    'd_10_2_2b_age_parent_unit': 'D.10.2.2b Age of Parent Unit',
    'd_10_3_last_menstrual_period_date_parent': 'D.10.3 Last Menstrual Period Date of Parent',
    'd_10_4_body_weight_parent': 'D.10.4 Body Weight of Parent (kg)',
    'd_10_5_height_parent': 'D.10.5 Height of Parent (cm)',
    'd_10_6_sex_parent': 'D.10.6 Sex of Parent',
    'd_10_7_1_r_structured_information_parent_meddra_code': 'D.10.7.1(R) Parent Medical History',
    'd_10_7_2_text_medical_history_parent': 'D.10.7.2 Text for Parent Medical History',
    'd_10_8_r_past_drug_history_parent': 'D.10.8(R) Past Drug History of Parent',
    'e_i_reaction_event': 'E.i Reaction(s) / Event(s)',
    'e_i_1_1a_reaction_primary_source_native_language': 'E.i.1.1a Reaction/Event as Reported (native language)',
    'e_i_1_1b_reaction_primary_source_language': 'E.i.1.1b Language',
    'e_i_1_2_reaction_primary_source_translation': 'E.i.1.2 Reaction/Event as Reported (English translation)',
    'e_i_2_1a_meddra_version_reaction': 'E.i.2.1a MedDRA Version (Reaction)',
    'e_i_2_1b_reaction_meddra_code': 'E.i.2.1b Reaction/Event MedDRA Code',
    'e_i_3_1_term_highlighted_reporter': 'E.i.3.1 Term Highlighted by Reporter',
    'e_i_3_2a_results_death': 'E.i.3.2a Results in Death',
    'e_i_3_2b_life_threatening': 'E.i.3.2b Life Threatening',
    'e_i_3_2c_caused_prolonged_hospitalisation': 'E.i.3.2c Caused/Prolonged Hospitalisation',
    'e_i_3_2d_disabling_incapacitating': 'E.i.3.2d Disabling/Incapacitating',
    'e_i_3_2e_congenital_anomaly_birth_defect': 'E.i.3.2e Congenital Anomaly / Birth Defect',
    'e_i_3_2f_other_medically_important_condition': 'E.i.3.2f Other Medically Important Condition',
    'e_i_4_date_start_reaction': 'E.i.4 Date of Start of Reaction/Event',
    'e_i_5_date_end_reaction': 'E.i.5 Date of End of Reaction/Event',
    'e_i_6a_duration_reaction_num': 'E.i.6a Duration of Reaction/Event (Number)',
    'e_i_6b_duration_reaction_unit': 'E.i.6b Duration Unit',
    'e_i_7_outcome_reaction_last_observation': 'E.i.7 Outcome of Reaction/Event at Last Observation',
    'e_i_8_medical_confirmation_healthcare_professional': 'E.i.8 Medical Confirmation by Healthcare Professional',
    'e_i_9_identification_country_reaction': 'E.i.9 Country Where Reaction Occurred',
    'f_r_results_tests_procedures_investigation_patient': 'F.r Results of Tests and Procedures',
    'f_r_1_test_date': 'F.r.1 Test Date',
    'f_r_2_1_test_name': 'F.r.2.1 Test Name',
    'f_r_2_2a_meddra_version_test_name': 'F.r.2.2a MedDRA Version (Test Name)',
    'f_r_2_2b_test_name_meddra_code': 'F.r.2.2b Test Name MedDRA Code',
    'f_r_3_1_test_result_code': 'F.r.3.1 Test Result (code)',
    'f_r_3_2_test_result_val_qual': 'F.r.3.2 Test Result (value/qualifier)',
    'f_r_3_3_test_result_unit': 'F.r.3.3 Test Result Unit',
    'f_r_3_4_result_unstructured_data': 'F.r.3.4 Result Unstructured Data',
    'f_r_4_normal_low_value': 'F.r.4 Normal Low Value',
    'f_r_5_normal_high_value': 'F.r.5 Normal High Value',
    'f_r_6_comments': 'F.r.6 Comments',
    'f_r_7_more_information_available': 'F.r.7 More Information Available',
    'g_k_drug_information': 'G.k Drug(s) Information',
    'g_k_1_characterisation_drug_role': 'G.k.1 Characterisation of Drug Role',
    'g_k_2_1_1a_mpid_version': 'G.k.2.1.1a MPID Version',
    'g_k_2_1_1b_mpid': 'G.k.2.1.1b Medicinal Product ID (MPID)',
    'g_k_2_1_2a_phpid_version': 'G.k.2.1.2a PhPID Version',
    'g_k_2_1_2b_phpid': 'G.k.2.1.2b Pharmaceutical Product ID (PhPID)',
    'g_k_2_2_medicinal_product_name_primary_source': 'G.k.2.2 Medicinal Product Name (Primary Source)',
    'g_k_2_3_r_substance_id_strength': 'G.k.2.3(R) Substance / Strength',
    'g_k_2_3_r_1_substance_name': 'G.k.2.3.r.1 Substance Name',
    'g_k_2_3_r_2a_substance_termid_version': 'G.k.2.3.r.2a Substance Term ID Version',
    'g_k_2_3_r_2b_substance_termid': 'G.k.2.3.r.2b Substance Term ID',
    'g_k_2_3_r_3a_strength_num': 'G.k.2.3.r.3a Strength (Number)',
    'g_k_2_3_r_3b_strength_unit': 'G.k.2.3.r.3b Strength Unit',
    'g_k_2_4_identification_country_drug_obtained': 'G.k.2.4 Country Where Drug Was Obtained',
    'g_k_2_5_investigational_product_blinded': 'G.k.2.5 Investigational Product Blinded',
    'g_k_3_1_authorisation_application_number': 'G.k.3.1 Authorisation / Application Number',
    'g_k_3_2_country_authorisation_application': 'G.k.3.2 Country of Authorisation / Application',
    'g_k_3_3_name_holder_applicant': 'G.k.3.3 Name of Holder / Applicant',
    'g_k_4_r_dosage_information': 'G.k.4(R) Dosage and Relevant Information',
    'g_k_4_r_1a_dose_num': 'G.k.4.r.1a Dose (Number)',
    'g_k_4_r_1b_dose_unit': 'G.k.4.r.1b Dose Unit',
    'g_k_4_r_2_number_units_interval': 'G.k.4.r.2 Number of Units in the Interval',
    'g_k_4_r_3_definition_interval_unit': 'G.k.4.r.3 Definition of the Interval Unit',
    'g_k_4_r_4_date_time_drug': 'G.k.4.r.4 Date/Time of Start of Drug',
    'g_k_4_r_5_date_time_last_administration': 'G.k.4.r.5 Date/Time of Last Administration',
    'g_k_4_r_6a_duration_drug_administration_num': 'G.k.4.r.6a Duration of Drug Administration (Number)',
    'g_k_4_r_6b_duration_drug_administration_unit': 'G.k.4.r.6b Duration of Drug Administration Unit',
    'g_k_4_r_7_batch_lot_number': 'G.k.4.r.7 Batch/Lot Number',
    'g_k_4_r_8_dosage_text': 'G.k.4.r.8 Dosage Text',
    'g_k_4_r_9_1_pharmaceutical_dose_form': 'G.k.4.r.9.1 Pharmaceutical Dose Form',
    'g_k_4_r_10_1_route_administration': 'G.k.4.r.10.1 Route of Administration',
    'g_k_4_r_11_1_parent_route_administration': 'G.k.4.r.11.1 Parent Route of Administration',
    'g_k_5a_cumulative_dose_first_reaction_num': 'G.k.5a Cumulative Dose to First Reaction (Number)',
    'g_k_5b_cumulative_dose_first_reaction_unit': 'G.k.5b Cumulative Dose Unit',
    'g_k_6a_gestation_period_exposure_num': 'G.k.6a Gestation Period at Time of Exposure (Number)',
    'g_k_6b_gestation_period_exposure_unit': 'G.k.6b Gestation Period Unit',
    'g_k_7_r_indication_use_case': 'G.k.7(R) Indication(s) for Use in Case',
    'g_k_7_r_1_indication_primary_source': 'G.k.7.r.1 Indication (Primary Source)',
    'g_k_7_r_2a_meddra_version_indication': 'G.k.7.r.2a MedDRA Version (Indication)',
    'g_k_7_r_2b_indication_meddra_code': 'G.k.7.r.2b Indication MedDRA Code',
    'g_k_8_action_taken_drug': 'G.k.8 Action(s) Taken with Drug',
    'g_k_9_i_drug_reaction_matrix': 'G.k.9.i Drug-Reaction Matrix',
    'g_k_9_i_1_reaction_assessed': 'G.k.9.i.1 Reaction/Event Assessed',
    'g_k_9_i_2_r_assessment_relatedness_drug_reaction': 'G.k.9.i.2(R) Assessment of Relatedness',
    'g_k_9_i_2_r_1_source_assessment': 'G.k.9.i.2.r.1 Source of Assessment',
    'g_k_9_i_2_r_2_method_assessment': 'G.k.9.i.2.r.2 Method of Assessment',
    'g_k_9_i_2_r_3_result_assessment': 'G.k.9.i.2.r.3 Result of Assessment',
    'g_k_9_i_3_1a_interval_drug_administration_reaction_num': 'G.k.9.i.3.1a Interval Drug→Reaction (Number)',
    'g_k_9_i_3_1b_interval_drug_administration_reaction_unit': 'G.k.9.i.3.1b Interval Unit',
    'g_k_9_i_3_2a_interval_last_dose_drug_reaction_num': 'G.k.9.i.3.2a Interval Last Dose→Reaction (Number)',
    'g_k_9_i_3_2b_interval_last_dose_drug_reaction_unit': 'G.k.9.i.3.2b Interval Unit',
    'g_k_9_i_4_reaction_recur_readministration': 'G.k.9.i.4 Reaction Recur on Readministration?',
    'g_k_10_r_additional_information_drug': 'G.k.10(R) Additional Information on Drug',
    'g_k_11_additional_information_drug': 'G.k.11 Additional Information on Drug (free text)',
    'h_narrative_case_summary': 'H Narrative Case Summary and Comments',
    'h_1_case_narrative': 'H.1 Case Narrative',
    'h_2_reporter_comments': "H.2 Reporter's Comments",
    'h_3_r_sender_diagnosis_meddra_code': "H.3(R) Sender's Diagnosis MedDRA Code",
    'h_3_r_1a_meddra_version_sender_diagnosis': 'H.3.r.1a MedDRA Version (Sender Diagnosis)',
    'h_3_r_1b_sender_diagnosis_meddra_code': "H.3.r.1b Sender's Diagnosis MedDRA Code",
    'h_4_sender_comments': "H.4 Sender's Comments",
    'h_5_r_case_summary_reporter_comments_native_language': 'H.5(R) Case Summary (native language)',
    'h_5_r_1a_case_summary_reporter_comments_text': 'H.5.r.1a Case Summary Text (native language)',
    'h_5_r_1b_case_summary_reporter_comments_language': 'H.5.r.1b Language',
}

ENUM_LABELS: Dict[str, Dict[str, str]] = {
    'c_1_3_type_report': {
        '1': 'Spontaneous Report',
        '2': 'Report from Study',
        '3': 'Other',
        '4': 'Not Available to Sender (from Study)',
    },
    'c_1_8_2_first_sender': {'1': 'Regulator', '2': 'Other'},
    'c_1_11_1_report_nullification_amendment': {'1': 'Nullification', '2': 'Amendment'},
    'c_2_r_4_qualification': {
        '1': 'Physician', '2': 'Pharmacist', '3': 'Other Health Professional',
        '4': 'Lawyer', '5': 'Consumer or Other Non-Health Professional',
    },
    'c_2_r_5_primary_source_regulatory_purposes': {'1': 'Primary'},
    'c_3_1_sender_type': {
        '1': 'Pharmaceutical Company', '2': 'Regulatory Authority', '3': 'Health Professional',
        '4': 'Regional Pharmacovigilance Centre',
        '5': 'WHO Collaborating Centres for International Drug Monitoring',
        '6': 'Other', '7': 'Patient or Consumer',
    },
    'c_5_4_study_type_reaction': {
        '1': 'Clinical Trials', '2': 'Individual Patient Use', '3': 'Other Studies',
    },
    'd_2_3_patient_age_group': {
        '0': 'Foetus', '1': 'Neonate', '2': 'Infant', '3': 'Child',
        '4': 'Adolescent', '5': 'Adult', '6': 'Elderly',
    },
    'd_5_sex': {'1': 'Male', '2': 'Female'},
    'd_10_6_sex_parent': {'1': 'Male', '2': 'Female'},
    'e_i_3_1_term_highlighted_reporter': {
        '1': 'Yes (Not Serious)', '2': 'No (Not Serious)',
        '3': 'Yes (Serious)', '4': 'No (Serious)',
    },
    'e_i_7_outcome_reaction_last_observation': {
        '0': 'Unknown', '1': 'Recovered/Resolved', '2': 'Recovering/Resolving',
        '3': 'Not Recovered/Not Resolved/Ongoing',
        '4': 'Recovered/Resolved with Sequelae', '5': 'Fatal',
    },
    'f_r_3_1_test_result_code': {
        '1': 'Positive', '2': 'Negative', '3': 'Borderline', '4': 'Inconclusive',
    },
    'g_k_1_characterisation_drug_role': {
        '1': 'Suspect', '2': 'Concomitant', '3': 'Interacting', '4': 'Drug Not Administered',
    },
    'g_k_8_action_taken_drug': {
        '0': 'Unknown', '1': 'Drug Withdrawn', '2': 'Dose Reduced',
        '3': 'Dose Increased', '4': 'Dose Not Changed', '9': 'Not Applicable',
    },
    'g_k_9_i_4_reaction_recur_readministration': {
        '1': 'Yes – Yes', '2': 'Yes – No', '3': 'Yes – Unknown', '4': 'No – Not Applicable',
    },
    'g_k_10_r_additional_information_drug': {
        '1': 'Counterfeit', '2': 'Overdose', '3': 'Drug Taken by the Father',
        '4': 'Drug Taken Beyond Expiry Date',
        '5': 'Batch/Lot Within Specifications', '6': 'Batch/Lot Not Within Specifications',
        '7': 'Medication Error', '8': 'Misuse', '9': 'Abuse',
        '10': 'Occupational Exposure', '11': 'Off-Label Use',
    },
}

NULL_FLAVOR_LABELS: Dict[str, str] = {
    'NI': 'No Information', 'MSK': 'Masked', 'UNK': 'Unknown',
    'NA': 'Not Applicable', 'ASKU': 'Asked But Unknown', 'NASK': 'Not Asked',
    'NINF': 'Negative Infinity', 'PINF': 'Positive Infinity',
}

AGE_UNIT_LABELS: Dict[str, str] = {
    '10.a': 'decade(s)', 'a': 'year(s)', 'mo': 'month(s)',
    'wk': 'week(s)', 'd': 'day(s)', 'h': 'hour(s)', 'min': 'minute(s)', 's': 'second(s)',
}

_LIST_TAGS = {
    'c_1_6_1_r_documents_held_sender', 'c_1_9_1_r_source_case_id',
    'c_1_10_r_identification_number_report_linked', 'c_2_r_primary_source_information',
    'c_4_r_literature_reference', 'c_5_1_r_study_registration',
    'd_7_1_r_structured_information_medical_history', 'd_8_r_past_drug_history',
    'd_9_2_r_cause_death', 'd_9_4_r_autopsy_determined_cause_death',
    'd_10_7_1_r_structured_information_parent_meddra_code', 'd_10_8_r_past_drug_history_parent',
    'e_i_reaction_event', 'f_r_results_tests_procedures_investigation_patient',
    'g_k_drug_information', 'g_k_2_3_r_substance_id_strength',
    'g_k_4_r_dosage_information', 'g_k_7_r_indication_use_case',
    'g_k_9_i_drug_reaction_matrix', 'g_k_9_i_2_r_assessment_relatedness_drug_reaction',
    'g_k_10_r_additional_information_drug', 'h_3_r_sender_diagnosis_meddra_code',
    'h_5_r_case_summary_reporter_comments_native_language',
}


# XML Parsing
def _elem_to_value(elem: ET.Element) -> Any:
    """
    Recursively convert an XML element to a Python value.

    Handles the application's internal XML format produced by xmltodict.unparse():
      - <field><value>X</value></field>           → "X"
      - <field><value/><null_flavor>NF</null_flavor></field> → {"_null_flavor": "NF"}
      - <field>...</field> (nested)               → dict
      - repeated same-tag siblings collected by caller → list
    """
    children = list(elem)

    if not children:
        t = elem.text
        return t.strip() if (t and t.strip()) else None

    child_tags = [c.tag for c in children]

    if 'value' in child_tags:
        val_elem = elem.find('value')
        nf_elem  = elem.find('null_flavor')

        raw_val = None
        if val_elem is not None:
            raw_val = (val_elem.text or '').strip() or None

        raw_nf = None
        if nf_elem is not None:
            raw_nf = (nf_elem.text or '').strip() or None

        if raw_nf:
            return {'_null_flavor': raw_nf, '_value': raw_val}
        return raw_val

    tag_counts: Dict[str, int] = {}
    for c in children:
        tag_counts[c.tag] = tag_counts.get(c.tag, 0) + 1

    result: Dict[str, Any] = {}
    list_buf: Dict[str, list] = {}

    for c in children:
        if c.tag == 'id':
            continue
        if c.tag == 'uuid':
            continue

        parsed = _elem_to_value(c)

        if tag_counts[c.tag] > 1 or c.tag in _LIST_TAGS:
            if c.tag not in list_buf:
                list_buf[c.tag] = []
            if parsed is not None and parsed != {} and parsed != '':
                list_buf[c.tag].append(parsed)
        else:
            result[c.tag] = parsed

    result.update(list_buf)
    return result


def _parse_xml(xml_string: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse E2B R3 XML. Auto-detects format:
      - Standard ICH HL7 v3 XML (MCCI_IN200100UV01 / urn:hl7-org:v3)
      - Application internal XML (produced by the to-xml endpoint)
    Returns (root_tag, data_dict).
    """
    xml_string = xml_string.strip()
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as exc:
        raise ValueError(f'Invalid XML: {exc}') from exc

    hl7_ns = 'urn:hl7-org:v3'
    local_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
    is_hl7 = (hl7_ns in root.tag or
              root.get('xmlns') == hl7_ns or
              local_tag in ('MCCI_IN200100UV01', 'PORR_IN049016UV'))

    if is_hl7:
        data = _parse_hl7_xml(root)
        return 'ICSR', data

    data = _elem_to_value(root)
    return root.tag, (data or {})


# Standard ICH E2B R3 HL7 v3 XML Parser
_HL7_NS  = 'urn:hl7-org:v3'
_XSI_NS  = 'http://www.w3.org/2001/XMLSchema-instance'


def _hl7(tag: str) -> str:
    return f'{{{_HL7_NS}}}{tag}'


def _xsi_type(elem: ET.Element) -> str:
    return elem.get(f'{{{_XSI_NS}}}type', '')


def _h(elem: Optional[ET.Element], *path: str) -> Optional[ET.Element]:
    """Walk a chain of HL7-namespaced child tags."""
    cur = elem
    for tag in path:
        if cur is None:
            return None
        cur = cur.find(_hl7(tag))
    return cur


def _htext(elem: Optional[ET.Element]) -> Optional[str]:
    if elem is None:
        return None
    t = elem.text
    return t.strip() if (t and t.strip()) else None


def _parse_hl7_xml(root: ET.Element) -> Dict[str, Any]:
    """
    Parse the official ICH E2B R3 HL7 v3 XML format
    (root tag MCCI_IN200100UV01 with namespace urn:hl7-org:v3).
    Returns an internal dict compatible with all converters.
    """
    data: Dict[str, Any] = {}

    local = root.tag.split('}')[-1]
    if local == 'MCCI_IN200100UV01':
        porr = root.find(_hl7('PORR_IN049016UV'))
    else:
        porr = root

    if porr is None:
        return data

    ctrl   = _h(porr, 'controlActProcess')
    invstg = _h(ctrl, 'subject', 'investigationEvent') if ctrl is not None else None

    if invstg is None:
        return data

    # C.1  Identification
    c1: Dict[str, Any] = {}

    for id_el in invstg.findall(_hl7('id')):
        r   = id_el.get('root', '')
        ext = id_el.get('extension', '')
        if r.endswith('.3.1'):
            c1['c_1_1_sender_safety_report_unique_id'] = ext
        elif r.endswith('.3.2'):
            c1['c_1_8_1_worldwide_unique_case_identification_number'] = ext

    # C.1.2  date of creation — effectiveTime of controlActProcess
    eff_ctrl = _h(ctrl, 'effectiveTime')
    if eff_ctrl is not None:
        c1['c_1_2_date_creation'] = eff_ctrl.get('value', '')

    # C.1.4  effectiveTime/low of investigationEvent
    low = _h(invstg, 'effectiveTime', 'low')
    if low is not None:
        c1['c_1_4_date_report_first_received_source'] = low.get('value', '')

    # C.1.5  availabilityTime
    avail = _h(invstg, 'availabilityTime')
    if avail is not None:
        c1['c_1_5_date_most_recent_information'] = avail.get('value', '')

    # C.1.3 / C.1.6.1 / C.1.7 / C.1.9.1  — from subjectOf2
    for s2 in invstg.findall(_hl7('subjectOf2')):
        ic = _h(s2, 'investigationCharacteristic')
        if ic is None:
            continue
        ic_code = _h(ic, 'code')
        ic_val  = _h(ic, 'value')
        if ic_code is None:
            continue
        cv = ic_code.get('code', '')
        if cv == '1' and ic_val is not None:
            c1['c_1_3_type_report'] = ic_val.get('code', '')
        elif cv == '2' and ic_val is not None:
            nf = ic_val.get('nullFlavor')
            c1['c_1_9_1_other_case_ids_previous_transmissions'] = (
                {'_null_flavor': nf} if nf else ic_val.get('value', ''))

    # C.1.6.1 / C.1.7  — from component > observationEvent
    for comp in invstg.findall(_hl7('component')):
        oe   = _h(comp, 'observationEvent')
        if oe is None:
            continue
        oe_c = _h(oe, 'code')
        oe_v = _h(oe, 'value')
        if oe_c is None or oe_v is None:
            continue
        cv = oe_c.get('code', '')
        if cv == '1':
            c1['c_1_6_1_additional_documents_available'] = oe_v.get('value', '')
        elif cv == '23':
            c1['c_1_7_fulfil_local_criteria_expedited_report'] = oe_v.get('value', '')

    # C.1.8.2  first sender — outboundRelationship code=1
    for obr in invstg.findall(_hl7('outboundRelationship')):
        ri   = _h(obr, 'relatedInvestigation')
        if ri is None:
            continue
        ri_c = _h(ri, 'code')
        if ri_c is not None and ri_c.get('code') == '1':
            ae_code = ri.find(
                f'.//{_hl7("subjectOf2")}/{_hl7("controlActEvent")}'
                f'/{_hl7("author")}/{_hl7("assignedEntity")}/{_hl7("code")}')
            if ae_code is not None:
                c1['c_1_8_2_first_sender'] = ae_code.get('code', '')

    # C.4  Literature reference
    lit_list = []
    for ref in invstg.findall(_hl7('reference')):
        doc  = _h(ref, 'document')
        bib  = _h(doc, 'bibliographicDesignationText') if doc is not None else None
        if bib is not None and bib.text:
            lit_list.append({'c_4_r_1_literature_reference': bib.text.strip()})

    data['c_1_identification_case_safety_report'] = c1
    if lit_list:
        data['c_4_r_literature_reference'] = lit_list

    aea = invstg.find(
        f'{_hl7("component")}/{_hl7("adverseEventAssessment")}')
    if aea is None:
        return data

    primary_role = _h(aea, 'subject1', 'primaryRole')

    # D  Patient characteristics
    if primary_role is not None:
        d: Dict[str, Any] = {}
        player = _h(primary_role, 'player1')
        if player is not None:
            name_el = _h(player, 'name')
            if name_el is not None and name_el.text:
                d['d_1_patient'] = name_el.text.strip()
            gender = _h(player, 'administrativeGenderCode')
            if gender is not None:
                d['d_5_sex'] = gender.get('code', '')
            birth = _h(player, 'birthTime')
            if birth is not None:
                d['d_2_1_date_birth'] = birth.get('value', '')

        for s2 in primary_role.findall(_hl7('subjectOf2')):
            obs = _h(s2, 'observation')
            if obs is not None:
                obs_c = _h(obs, 'code')
                obs_v = _h(obs, 'value')
                if obs_c is None:
                    continue
                cv = obs_c.get('code', '')
                if cv == '3' and obs_v is not None:
                    d['d_2_2a_age_onset_reaction_num'] = obs_v.get('value', '')
                    d['d_2_2b_age_onset_reaction_unit'] = obs_v.get('unit', '')
                elif cv == '7' and obs_v is not None:
                    d['d_3_body_weight'] = obs_v.get('value', '')
                elif cv == '17' and obs_v is not None:
                    d['d_4_height'] = obs_v.get('value', '')
                elif cv == '22':
                    if obs_v is not None:
                        nf = obs_v.get('nullFlavor')
                        d['d_6_last_menstrual_period_date'] = (
                            {'_null_flavor': nf} if nf else obs_v.get('value', ''))

            # D.7.1  structured medical history
            org = _h(s2, 'organizer')
            if org is not None:
                org_c = _h(org, 'code')
                if org_c is not None and org_c.get('code') == '1':
                    mh_list = []
                    for comp2 in org.findall(_hl7('component')):
                        obs2 = _h(comp2, 'observation')
                        if obs2 is None:
                            continue
                        mh: Dict[str, Any] = {}
                        oc2 = _h(obs2, 'code')
                        if oc2 is not None:
                            mh['d_7_1_r_1a_meddra_version_medical_history'] = oc2.get('codeSystemVersion', '')
                            mh['d_7_1_r_1b_medical_history_meddra_code']    = oc2.get('code', '')
                        low2 = obs2.find(f'.//{_hl7("effectiveTime")}/{_hl7("low")}')
                        if low2 is not None:
                            mh['d_7_1_r_2_start_date'] = low2.get('value', '')
                        cont = obs2.find(
                            f'.//{_hl7("inboundRelationship")}/{_hl7("observation")}/{_hl7("value")}')
                        if cont is not None:
                            mh['d_7_1_r_3_continuing'] = cont.get('value', '')
                        if mh:
                            mh_list.append(mh)
                    if mh_list:
                        d['d_7_1_r_structured_information_medical_history'] = mh_list

            # E  Reactions (observation code=29)
            obs_e = _h(s2, 'observation')
            if obs_e is not None:
                obs_ec = _h(obs_e, 'code')
                if obs_ec is not None and obs_ec.get('code') == '29':
                    e: Dict[str, Any] = {}
                    eff_e = _h(obs_e, 'effectiveTime')
                    if eff_e is not None:
                        for comp_e in eff_e.findall(_hl7('comp')):
                            tp = _xsi_type(comp_e)
                            if 'IVL_TS' in tp and 'operator' not in comp_e.attrib:
                                low_e = _h(comp_e, 'low')
                                high_e = _h(comp_e, 'high')
                                if low_e is not None:
                                    e['e_i_4_date_start_reaction'] = low_e.get('value', '')
                                if high_e is not None:
                                    e['e_i_5_date_end_reaction'] = high_e.get('value', '')
                            elif 'IVL_TS' in tp and comp_e.get('operator') == 'A':
                                w = _h(comp_e, 'width')
                                if w is not None:
                                    e['e_i_6a_duration_reaction_num']  = w.get('value', '')
                                    e['e_i_6b_duration_reaction_unit'] = w.get('unit', '')

                    val_e = _h(obs_e, 'value')
                    if val_e is not None:
                        e['e_i_2_1a_meddra_version_reaction'] = val_e.get('codeSystemVersion', '')
                        e['e_i_2_1b_reaction_meddra_code']    = val_e.get('code', '')
                        orig_e = _h(val_e, 'originalText')
                        if orig_e is not None and orig_e.text:
                            e['e_i_1_1a_reaction_primary_source_native_language'] = orig_e.text.strip()
                            e['e_i_1_1b_reaction_primary_source_language']        = orig_e.get('language', '')

                    country_e = obs_e.find(
                        f'.//{_hl7("locatedPlace")}/{_hl7("code")}')
                    if country_e is not None:
                        e['e_i_9_identification_country_reaction'] = country_e.get('code', '')

                    _SERIOUSNESS = {
                        '34': 'e_i_3_2a_results_death',
                        '21': 'e_i_3_2b_life_threatening',
                        '33': 'e_i_3_2c_caused_prolonged_hospitalisation',
                        '35': 'e_i_3_2d_disabling_incapacitating',
                        '12': 'e_i_3_2e_congenital_anomaly_birth_defect',
                        '26': 'e_i_3_2f_other_medically_important_condition',
                    }
                    for obr2 in obs_e.findall(_hl7('outboundRelationship2')):
                        obs2 = _h(obr2, 'observation')
                        if obs2 is None:
                            continue
                        c2_el = _h(obs2, 'code')
                        v2_el = _h(obs2, 'value')
                        if c2_el is None:
                            continue
                        cv2 = c2_el.get('code', '')
                        if cv2 == '30' and v2_el is not None:
                            e['e_i_1_2_reaction_primary_source_translation'] = (
                                v2_el.text.strip() if v2_el.text else '')
                        elif cv2 == '37' and v2_el is not None:
                            e['e_i_3_1_term_highlighted_reporter'] = v2_el.get('code', '')
                        elif cv2 == '27' and v2_el is not None:
                            e['e_i_7_outcome_reaction_last_observation'] = v2_el.get('code', '')
                        elif cv2 in _SERIOUSNESS and v2_el is not None:
                            nf = v2_el.get('nullFlavor')
                            e[_SERIOUSNESS[cv2]] = (
                                {'_null_flavor': nf} if nf else v2_el.get('value', ''))

                    reactions = data.get('e_i_reaction_event', [])
                    reactions.append(e)
                    data['e_i_reaction_event'] = reactions

            # F  Tests (organizer code=3)
            org_f = _h(s2, 'organizer')
            if org_f is not None:
                org_fc = _h(org_f, 'code')
                if org_fc is not None and org_fc.get('code') == '3':
                    f_list = []
                    for comp_f in org_f.findall(_hl7('component')):
                        obs_f = _h(comp_f, 'observation')
                        if obs_f is None:
                            continue
                        f_entry: Dict[str, Any] = {}
                        oc_f = _h(obs_f, 'code')
                        eff_f = _h(obs_f, 'effectiveTime')
                        if eff_f is not None:
                            f_entry['f_r_1_test_date'] = eff_f.get('value', '')
                        if oc_f is not None:
                            f_entry['f_r_2_2b_test_name_meddra_code']     = oc_f.get('code', '')
                            f_entry['f_r_2_2a_meddra_version_test_name']  = oc_f.get('codeSystemVersion', '')
                            orig_f = _h(oc_f, 'originalText')
                            if orig_f is not None and orig_f.text:
                                f_entry['f_r_2_1_test_name'] = orig_f.text.strip()
                        val_f = _h(obs_f, 'value')
                        if val_f is not None:
                            tp_f = _xsi_type(val_f)
                            if 'IVL_PQ' in tp_f:
                                ctr = _h(val_f, 'center')
                                if ctr is not None:
                                    f_entry['f_r_3_2_test_result_val_qual'] = ctr.get('value', '')
                                    f_entry['f_r_3_3_test_result_unit']     = ctr.get('unit', '')
                            elif 'PQ' in tp_f:
                                f_entry['f_r_3_2_test_result_val_qual'] = val_f.get('value', '')
                                f_entry['f_r_3_3_test_result_unit']     = val_f.get('unit', '')
                            elif 'ED' in tp_f:
                                f_entry['f_r_3_4_result_unstructured_data'] = (
                                    val_f.text.strip() if val_f.text else '')
                        rr = obs_f.find(
                            f'.//{_hl7("referenceRange")}/{_hl7("observationRange")}')
                        if rr is not None:
                            rr_v    = _h(rr, 'value')
                            rr_interp = _h(rr, 'interpretationCode')
                            if rr_v is not None and rr_interp is not None:
                                key = ('f_r_5_normal_high_value'
                                       if rr_interp.get('code') == 'H'
                                       else 'f_r_4_normal_low_value')
                                f_entry[key] = rr_v.get('value', '')
                        for obr2f in obs_f.findall(_hl7('outboundRelationship2')):
                            obs2f = _h(obr2f, 'observation')
                            if obs2f is None:
                                continue
                            c2f = _h(obs2f, 'code')
                            v2f = _h(obs2f, 'value')
                            if c2f is not None and c2f.get('code') == '25' and v2f is not None:
                                f_entry['f_r_7_more_information_available'] = v2f.get('value', '')
                        if f_entry:
                            f_list.append(f_entry)
                    if f_list:
                        data['f_r_results_tests_procedures_investigation_patient'] = f_list

            # G  Drugs (organizer code=4)
            org_g = _h(s2, 'organizer')
            if org_g is not None:
                org_gc = _h(org_g, 'code')
                if org_gc is not None and org_gc.get('code') == '4':
                    for comp_g in org_g.findall(_hl7('component')):
                        sa = _h(comp_g, 'substanceAdministration')
                        if sa is None:
                            continue
                        g: Dict[str, Any] = {}
                        kind = sa.find(f'.//{_hl7("kindOfProduct")}')
                        if kind is not None:
                            nm = _h(kind, 'name')
                            if nm is not None and nm.text:
                                g['g_k_2_2_medicinal_product_name_primary_source'] = nm.text.strip()
                            kc = _h(kind, 'code')
                            if kc is not None:
                                g['g_k_2_1_1a_mpid_version'] = kc.get('codeSystemVersion', '')
                                g['g_k_2_1_1b_mpid']         = kc.get('code', '')
                            approval = kind.find(f'.//{_hl7("approval")}')
                            if approval is not None:
                                apid = _h(approval, 'id')
                                if apid is not None:
                                    g['g_k_3_1_authorisation_application_number'] = apid.get('extension', '')
                                holder_nm = approval.find(
                                    f'.//{_hl7("playingOrganization")}/{_hl7("name")}')
                                if holder_nm is not None and holder_nm.text:
                                    g['g_k_3_3_name_holder_applicant'] = holder_nm.text.strip()
                                terr = approval.find(f'.//{_hl7("territory")}/{_hl7("code")}')
                                if terr is not None:
                                    g['g_k_3_2_country_authorisation_application'] = terr.get('code', '')
                            ingr = _h(kind, 'ingredient')
                            if ingr is not None:
                                subst = _h(ingr, 'ingredientSubstance')
                                if subst is not None:
                                    g_sub: Dict[str, Any] = {}
                                    sn = _h(subst, 'name')
                                    if sn is not None and sn.text:
                                        g_sub['g_k_2_3_r_1_substance_name'] = sn.text.strip()
                                    sc = _h(subst, 'code')
                                    if sc is not None:
                                        g_sub['g_k_2_3_r_2a_substance_termid_version'] = sc.get('codeSystemVersion', '')
                                        g_sub['g_k_2_3_r_2b_substance_termid']         = sc.get('code', '')
                                    num = _h(ingr, 'quantity', 'numerator')
                                    if num is not None:
                                        g_sub['g_k_2_3_r_3a_strength_num']  = num.get('value', '')
                                        g_sub['g_k_2_3_r_3b_strength_unit'] = num.get('unit', '')
                                    if g_sub:
                                        g['g_k_2_3_r_substance_id_strength'] = [g_sub]
                            country_obt = kind.find(
                                f'.//{_hl7("addr")}/{_hl7("country")}')
                            if country_obt is not None and country_obt.text:
                                g['g_k_2_4_identification_country_drug_obtained'] = country_obt.text.strip()

                        # Dosage
                        dos_list = []
                        for obr2g in sa.findall(_hl7('outboundRelationship2')):
                            sa2 = _h(obr2g, 'substanceAdministration')
                            if sa2 is None:
                                continue
                            dos: Dict[str, Any] = {}
                            dq = _h(sa2, 'doseQuantity')
                            if dq is not None:
                                dos['g_k_4_r_1a_dose_num']  = dq.get('value', '')
                                dos['g_k_4_r_1b_dose_unit'] = dq.get('unit', '')
                            eff_g = _h(sa2, 'effectiveTime')
                            if eff_g is not None:
                                for comp2g in eff_g.findall(_hl7('comp')):
                                    tp2 = _xsi_type(comp2g)
                                    if 'IVL_TS' in tp2:
                                        low_g  = _h(comp2g, 'low')
                                        high_g = _h(comp2g, 'high')
                                        if low_g is not None:
                                            dos['g_k_4_r_4_date_time_drug'] = low_g.get('value', '')
                                        if high_g is not None:
                                            dos['g_k_4_r_5_date_time_last_administration'] = high_g.get('value', '')
                                    elif 'PIVL_TS' in tp2:
                                        per = _h(comp2g, 'period')
                                        if per is not None:
                                            dos['g_k_4_r_2_number_units_interval']   = per.get('value', '')
                                            dos['g_k_4_r_3_definition_interval_unit'] = per.get('unit', '')
                            rc = _h(sa2, 'routeCode')
                            if rc is not None:
                                orig_r = _h(rc, 'originalText')
                                dos['g_k_4_r_10_1_route_administration'] = (
                                    orig_r.text.strip() if (orig_r is not None and orig_r.text)
                                    else rc.get('code', ''))
                            fc = sa2.find(f'.//{_hl7("formCode")}/{_hl7("originalText")}')
                            if fc is not None and fc.text:
                                dos['g_k_4_r_9_1_pharmaceutical_dose_form'] = fc.text.strip()
                            if dos:
                                dos_list.append(dos)
                        if dos_list:
                            g['g_k_4_r_dosage_information'] = dos_list

                        # Indication
                        ind_list = []
                        for ibr in sa.findall(_hl7('inboundRelationship')):
                            ibr_obs = _h(ibr, 'observation')
                            ibr_act = _h(ibr, 'act')
                            if ibr_obs is not None:
                                ibr_c = _h(ibr_obs, 'code')
                                ibr_v = _h(ibr_obs, 'value')
                                if ibr_c is not None and ibr_c.get('code') == '19' and ibr_v is not None:
                                    ind: Dict[str, Any] = {
                                        'g_k_7_r_2a_meddra_version_indication': ibr_v.get('codeSystemVersion', ''),
                                        'g_k_7_r_2b_indication_meddra_code':    ibr_v.get('code', ''),
                                    }
                                    orig_i = _h(ibr_v, 'originalText')
                                    if orig_i is not None and orig_i.text:
                                        ind['g_k_7_r_1_indication_primary_source'] = orig_i.text.strip()
                                    ind_list.append(ind)
                            if ibr_act is not None:
                                ac = _h(ibr_act, 'code')
                                if ac is not None:
                                    g['g_k_8_action_taken_drug'] = ac.get('code', '')
                        if ind_list:
                            g['g_k_7_r_indication_use_case'] = ind_list

                        drugs = data.get('g_k_drug_information', [])
                        drugs.append(g)
                        data['g_k_drug_information'] = drugs

        if d:
            data['d_patient_characteristics'] = d

    # G.k.1 drug role — from causalityAssessment code=20
    drugs = data.get('g_k_drug_information', [])
    drug_roles: List[str] = []
    for comp_ca in aea.findall(_hl7('component')):
        ca = _h(comp_ca, 'causalityAssessment')
        if ca is None:
            continue
        ca_c = _h(ca, 'code')
        ca_v = _h(ca, 'value')
        if ca_c is not None and ca_c.get('code') == '20' and ca_v is not None:
            drug_roles.append(ca_v.get('code', ''))
    for i, role in enumerate(drug_roles):
        if i < len(drugs):
            drugs[i]['g_k_1_characterisation_drug_role'] = role

    # C.2  Primary source
    c2_list = []
    for obr in invstg.findall(_hl7('outboundRelationship')):
        ri   = _h(obr, 'relatedInvestigation')
        if ri is None:
            continue
        ri_c = _h(ri, 'code')
        if ri_c is None or ri_c.get('code') != '2':
            continue
        ae   = _h(ri, 'subjectOf2', 'controlActEvent', 'author', 'assignedEntity')
        if ae is None:
            continue
        c2: Dict[str, Any] = {}
        pri = _h(obr, 'priorityNumber')
        if pri is not None:
            c2['c_2_r_5_primary_source_regulatory_purposes'] = pri.get('value', '')
        addr = _h(ae, 'addr')
        if addr is not None:
            for tag_name, field in [
                ('streetAddressLine', 'c_2_r_2_3_reporter_street'),
                ('city',              'c_2_r_2_4_reporter_city'),
                ('state',             'c_2_r_2_5_reporter_state_province'),
                ('postalCode',        'c_2_r_2_6_reporter_postcode'),
            ]:
                el = _h(addr, tag_name)
                if el is not None and el.text:
                    c2[field] = el.text.strip()
        person = _h(ae, 'assignedPerson')
        if person is not None:
            nm = _h(person, 'name')
            if nm is not None:
                gv = _h(nm, 'given')
                fm = _h(nm, 'family')
                if gv is not None and gv.text:
                    c2['c_2_r_1_2_reporter_given_name'] = gv.text.strip()
                if fm is not None and fm.text:
                    c2['c_2_r_1_4_reporter_family_name'] = fm.text.strip()
            qual_c = person.find(f'.//{_hl7("asQualifiedEntity")}/{_hl7("code")}')
            if qual_c is not None:
                c2['c_2_r_4_qualification'] = qual_c.get('code', '')
            cnt_c = person.find(f'.//{_hl7("asLocatedEntity")}/{_hl7("location")}/{_hl7("code")}')
            if cnt_c is not None:
                c2['c_2_r_3_reporter_country_code'] = cnt_c.get('code', '')
        org = _h(ae, 'representedOrganization')
        if org is not None:
            dep = _h(org, 'name')
            if dep is not None and dep.text:
                c2['c_2_r_2_2_reporter_department'] = dep.text.strip()
            sub_org = org.find(
                f'.//{_hl7("assignedEntity")}/{_hl7("representedOrganization")}/{_hl7("name")}')
            if sub_org is not None and sub_org.text:
                c2['c_2_r_2_1_reporter_organisation'] = sub_org.text.strip()
        c2_list.append(c2)
    if c2_list:
        data['c_2_r_primary_source_information'] = c2_list

    # C.3  Sender
    sender_ae = invstg.find(
        f'.//{_hl7("subjectOf1")}/{_hl7("controlActEvent")}'
        f'/{_hl7("author")}/{_hl7("assignedEntity")}')
    if sender_ae is not None:
        c3: Dict[str, Any] = {}
        sc = _h(sender_ae, 'code')
        if sc is not None:
            c3['c_3_1_sender_type'] = sc.get('code', '')
        addr3 = _h(sender_ae, 'addr')
        if addr3 is not None:
            for tag_name, field in [
                ('streetAddressLine', 'c_3_4_1_sender_street_address'),
                ('city',              'c_3_4_2_sender_city'),
                ('state',             'c_3_4_3_sender_state_province'),
                ('postalCode',        'c_3_4_4_sender_postcode'),
            ]:
                el = _h(addr3, tag_name)
                if el is not None and el.text:
                    c3[field] = el.text.strip()
        for tc in sender_ae.findall(_hl7('telecom')):
            v = tc.get('value', '')
            if v.startswith('tel:'):
                c3['c_3_4_6_sender_telephone'] = v[4:]
            elif v.startswith('fax:'):
                c3['c_3_4_7_sender_fax'] = v[4:]
            elif v.startswith('mailto:'):
                c3['c_3_4_8_sender_email'] = v[7:]
        p3 = _h(sender_ae, 'assignedPerson')
        if p3 is not None:
            nm3 = _h(p3, 'name')
            if nm3 is not None:
                gv3 = _h(nm3, 'given')
                fm3 = _h(nm3, 'family')
                if gv3 is not None and gv3.text:
                    c3['c_3_3_3_sender_given_name'] = gv3.text.strip()
                if fm3 is not None and fm3.text:
                    c3['c_3_3_5_sender_family_name'] = fm3.text.strip()
            cnt3 = p3.find(f'.//{_hl7("asLocatedEntity")}/{_hl7("location")}/{_hl7("code")}')
            if cnt3 is not None:
                c3['c_3_4_5_sender_country_code'] = cnt3.get('code', '')
        org3 = _h(sender_ae, 'representedOrganization')
        if org3 is not None:
            dep3 = _h(org3, 'name')
            if dep3 is not None and dep3.text:
                c3['c_3_3_1_sender_department'] = dep3.text.strip()
            sub3 = org3.find(
                f'.//{_hl7("assignedEntity")}/{_hl7("representedOrganization")}/{_hl7("name")}')
            if sub3 is not None and sub3.text:
                c3['c_3_2_sender_organisation'] = sub3.text.strip()
        data['c_3_information_sender_case_safety_report'] = c3

    # H  Narrative
    h: Dict[str, Any] = {}
    txt_el = _h(invstg, 'text')
    if txt_el is not None and txt_el.text:
        h['h_1_case_narrative'] = txt_el.text.strip()

    for comp_h in aea.findall(_hl7('component1')):
        oe_h  = _h(comp_h, 'observationEvent')
        if oe_h is None:
            continue
        oe_hc = _h(oe_h, 'code')
        oe_hv = _h(oe_h, 'value')
        auth_c = oe_h.find(
            f'.//{_hl7("author")}/{_hl7("assignedEntity")}/{_hl7("code")}')
        if oe_hc is None or oe_hv is None:
            continue
        if oe_hc.get('code') != '10':
            continue
        val_text = oe_hv.text.strip() if oe_hv.text else ''
        ac = auth_c.get('code', '') if auth_c is not None else ''
        if ac == '3':
            h['h_2_reporter_comments'] = val_text
        elif ac == '1':
            h['h_4_sender_comments'] = val_text

    h5_list = []
    for comp_h5 in invstg.findall(_hl7('component')):
        oe5 = _h(comp_h5, 'observationEvent')
        if oe5 is None:
            continue
        c5 = _h(oe5, 'code')
        v5 = _h(oe5, 'value')
        if c5 is None or c5.get('code') != '36' or v5 is None:
            continue
        h5_list.append({
            'h_5_r_1a_case_summary_reporter_comments_text':     v5.text.strip() if v5.text else '',
            'h_5_r_1b_case_summary_reporter_comments_language': v5.get('language', ''),
        })
    if h5_list:
        h['h_5_r_case_summary_reporter_comments_native_language'] = h5_list

    if h:
        data['h_narrative_case_summary'] = h

    return data


# Helpers
def _fmt_date(hl7: Optional[str]) -> str:
    """Convert HL7 compact date (YYYYMMDD…) to ISO-style string."""
    if not hl7:
        return ''
    s = str(hl7).strip()
    if re.match(r'^\d{8}$', s):
        return f'{s[0:4]}-{s[4:6]}-{s[6:8]}'
    if re.match(r'^\d{6}$', s):
        return f'{s[0:4]}-{s[4:6]}'
    if re.match(r'^\d{4}$', s):
        return s
    return s


def _resolve_enum(field: str, raw: Optional[str]) -> str:
    """Return human-readable label for an enum field value, or raw value."""
    if raw is None:
        return ''
    mapping = ENUM_LABELS.get(field, {})
    return mapping.get(str(raw), str(raw))


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace('_', ' ').title())


def _fmt_val(field: str, raw: Any) -> str:
    """Format a raw parsed value for display (HTML/JSON)."""
    if raw is None:
        return ''
    if isinstance(raw, dict):
        nf = raw.get('_null_flavor')
        if nf:
            return f'[{NULL_FLAVOR_LABELS.get(nf, nf)}]'
        return str(raw.get('_value') or '')
    resolved = _resolve_enum(field, str(raw))
    if any(kw in field for kw in ('date', 'birth', 'creation', 'received', 'recent',
                                   'death', 'start', 'end', 'last_administration',
                                   'date_time')):
        return _fmt_date(resolved) or resolved
    return resolved


def _scalar(raw: Any) -> Optional[str]:
    """Extract scalar string from parsed value."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        v = raw.get('_value')
        return str(v) if v is not None else None
    return str(raw)


# JSON Converter

def _clean_for_json(data: Any, include_empty: bool = False) -> Any:
    """Recursively clean parsed dict for JSON output."""
    if data is None:
        return None
    if isinstance(data, list):
        items = [_clean_for_json(i, include_empty) for i in data]
        if not include_empty:
            items = [i for i in items if i not in (None, {}, [], '')]
        return items
    if isinstance(data, dict):
        if '_null_flavor' in data:
            return {'null_flavor': data['_null_flavor'], 'value': data.get('_value')}
        result = {}
        for k, v in data.items():
            cleaned = _clean_for_json(v, include_empty)
            if include_empty or cleaned not in (None, {}, [], ''):
                result[k] = cleaned
        return result
    return data


def _to_json(data: Dict[str, Any], root_tag: str,
             indent: int = 2, include_empty: bool = False) -> str:
    """Convert parsed dict to clean JSON string."""
    cleaned = _clean_for_json(data, include_empty)
    wrapper = {root_tag: cleaned}
    return json.dumps(wrapper, ensure_ascii=False, indent=indent, default=str)


# HTML Report Generator

_HTML_CSS = """
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1a1a2e;
    background: #f4f6fb;
    margin: 0;
    padding: 20px;
  }
  .report-wrapper {
    max-width: 960px;
    margin: 0 auto;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,.12);
    overflow: hidden;
  }
  .report-header {
    background: linear-gradient(135deg, #1a237e 0%, #283593 60%, #3949ab 100%);
    color: #fff;
    padding: 28px 36px 20px;
  }
  .report-header h1 { margin: 0 0 4px; font-size: 22px; letter-spacing: .5px; }
  .report-header .subtitle { font-size: 12px; opacity: .8; margin-bottom: 12px; }
  .report-header .meta { display: flex; gap: 32px; flex-wrap: wrap; }
  .report-header .meta-item { font-size: 12px; }
  .report-header .meta-item strong { display: block; font-size: 13px; }
  .report-body { padding: 24px 36px 32px; }
  .section {
    margin-bottom: 20px;
    border: 1px solid #e0e4ef;
    border-radius: 6px;
    overflow: hidden;
  }
  .section-title {
    background: #e8eaf6;
    color: #1a237e;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 14px;
    text-transform: uppercase;
    letter-spacing: .6px;
    border-bottom: 1px solid #c5cae9;
  }
  .section-body { padding: 12px 14px; }
  table.fields {
    width: 100%;
    border-collapse: collapse;
  }
  table.fields td {
    padding: 5px 8px;
    vertical-align: top;
    border-bottom: 1px solid #f0f2f8;
    font-size: 12.5px;
  }
  table.fields tr:last-child td { border-bottom: none; }
  table.fields td.field-label {
    width: 46%;
    color: #5c6bc0;
    font-weight: 500;
  }
  table.fields td.field-value { color: #212121; }
  .badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge-yes  { background: #ffebee; color: #c62828; }
  .badge-no   { background: #e8f5e9; color: #2e7d32; }
  .badge-nf   { background: #fff8e1; color: #f57f17; font-style: italic; }
  .subsection-list { margin-top: 8px; }
  .subsection-item {
    background: #fafbff;
    border: 1px solid #e8eaf6;
    border-radius: 4px;
    margin-bottom: 8px;
    padding: 10px 12px;
  }
  .subsection-item:last-child { margin-bottom: 0; }
  .subsection-index {
    font-size: 11px;
    color: #7986cb;
    font-weight: 700;
    margin-bottom: 6px;
    text-transform: uppercase;
  }
  .narrative-block {
    background: #f8f9ff;
    border-left: 3px solid #5c6bc0;
    padding: 12px 14px;
    font-size: 12.5px;
    line-height: 1.7;
    white-space: pre-wrap;
    border-radius: 0 4px 4px 0;
  }
  .seriousness-flags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
  .report-footer {
    text-align: center;
    font-size: 11px;
    color: #9e9e9e;
    padding: 12px;
    border-top: 1px solid #e0e4ef;
  }
</style>
"""


def _bool_badge(val: Any) -> str:
    s = str(val).lower()
    if s in ('true', '1', 'yes'):
        return '<span class="badge badge-yes">YES</span>'
    if s in ('false', '0', 'no'):
        return '<span class="badge badge-no">NO</span>'
    return he(str(val))


def _nf_badge(nf_code: str) -> str:
    label = NULL_FLAVOR_LABELS.get(nf_code, nf_code)
    return f'<span class="badge badge-nf">[{he(label)}]</span>'


def _render_fields_table(fields: Dict[str, Any]) -> str:
    rows = []
    for field, raw in fields.items():
        if raw is None or raw == {} or raw == [] or raw == '':
            continue
        if isinstance(raw, (dict, list)):
            continue
        label = _label(field)
        display = he(_fmt_val(field, raw))
        if str(raw).lower() in ('true', 'false', '1', '0'):
            display = _bool_badge(raw)
        rows.append(
            f'<tr><td class="field-label">{he(label)}</td>'
            f'<td class="field-value">{display}</td></tr>'
        )
    if not rows:
        return ''
    return '<table class="fields">' + ''.join(rows) + '</table>'


def _render_obj(data: Dict[str, Any], depth: int = 0) -> str:
    """Render a dict of fields + nested lists as HTML."""
    parts = []
    scalars = {k: v for k, v in data.items()
               if not isinstance(v, (dict, list))}
    parts.append(_render_fields_table(scalars))

    for key, val in data.items():
        if isinstance(val, list) and val:
            items_html = []
            for idx, item in enumerate(val, 1):
                if isinstance(item, dict):
                    inner = _render_obj(item, depth + 1)
                else:
                    inner = he(str(item))
                items_html.append(
                    f'<div class="subsection-item">'
                    f'<div class="subsection-index">#{idx}</div>{inner}</div>'
                )
            parts.append(
                f'<div style="margin-top:8px"><strong style="font-size:12px;color:#5c6bc0">'
                f'{he(_label(key))}</strong>'
                f'<div class="subsection-list">{"".join(items_html)}</div></div>'
            )
        elif isinstance(val, dict):
            if '_null_flavor' in val:
                pass
            else:
                inner = _render_obj(val, depth + 1)
                parts.append(
                    f'<div style="margin-top:8px"><strong style="font-size:12px;color:#5c6bc0">'
                    f'{he(_label(key))}</strong><div style="margin-left:10px">{inner}</div></div>'
                )
    return ''.join(p for p in parts if p)


def _to_html(data: Dict[str, Any], root_tag: str) -> str:
    """Generate a professional HTML report from parsed ICSR data."""

    c1 = data.get('c_1_identification_case_safety_report') or {}
    case_id   = _scalar(c1.get('c_1_1_sender_safety_report_unique_id')) or 'N/A'
    wwuid     = _scalar(c1.get('c_1_8_1_worldwide_unique_case_identification_number')) or 'N/A'
    date_cr   = _fmt_date(_scalar(c1.get('c_1_2_date_creation'))) or 'N/A'
    type_code = _scalar(c1.get('c_1_3_type_report'))
    rtype     = _resolve_enum('c_1_3_type_report', type_code) if type_code else 'N/A'

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

    header = f"""
    <div class="report-header">
      <h1>Individual Case Safety Report (ICSR)</h1>
      <div class="subtitle">ICH E2B(R3) &mdash; Pharmacovigilance Report</div>
      <div class="meta">
        <div class="meta-item"><strong>{he(case_id)}</strong>Sender Report ID</div>
        <div class="meta-item"><strong>{he(wwuid)}</strong>Worldwide Unique Case ID</div>
        <div class="meta-item"><strong>{he(date_cr)}</strong>Date of Creation</div>
        <div class="meta-item"><strong>{he(rtype)}</strong>Report Type</div>
        <div class="meta-item"><strong>{now_str}</strong>Exported at</div>
      </div>
    </div>
    """

    SECTIONS = [
        ('c_1_identification_case_safety_report', 'C.1 — Identification of the Case Safety Report'),
        ('c_2_r_primary_source_information',      'C.2 — Primary Source Information'),
        ('c_3_information_sender_case_safety_report', 'C.3 — Information Sender'),
        ('c_4_r_literature_reference',            'C.4 — Literature Reference'),
        ('c_5_study_identification',              'C.5 — Study Identification'),
        ('d_patient_characteristics',             'D — Patient Characteristics'),
        ('e_i_reaction_event',                    'E — Reaction(s) / Event(s)'),
        ('f_r_results_tests_procedures_investigation_patient', 'F — Results of Tests and Procedures'),
        ('g_k_drug_information',                  'G — Drug(s) Information'),
        ('h_narrative_case_summary',              'H — Narrative Case Summary'),
    ]

    body_parts = []
    for key, title in SECTIONS:
        val = data.get(key)
        if val is None or val == [] or val == {}:
            continue

        if isinstance(val, list):
            items_html = []
            for idx, item in enumerate(val, 1):
                inner = _render_obj(item) if isinstance(item, dict) else he(str(item))
                items_html.append(
                    f'<div class="subsection-item">'
                    f'<div class="subsection-index">Entry #{idx}</div>{inner}</div>'
                )
            content = f'<div class="section-body"><div class="subsection-list">{"".join(items_html)}</div></div>'
        else:
            if key == 'h_narrative_case_summary':
                narrative = _scalar(val.get('h_1_case_narrative', '')) or ''
                reporter  = _scalar(val.get('h_2_reporter_comments', '')) or ''
                sender    = _scalar(val.get('h_4_sender_comments', '')) or ''
                inner = ''
                if narrative:
                    inner += (f'<div style="margin-bottom:10px"><div class="field-label" '
                              f'style="color:#5c6bc0;font-weight:600;margin-bottom:4px">'
                              f'{he(_label("h_1_case_narrative"))}</div>'
                              f'<div class="narrative-block">{he(narrative)}</div></div>')
                if reporter:
                    inner += (f'<div style="margin-bottom:10px"><div class="field-label" '
                              f'style="color:#5c6bc0;font-weight:600;margin-bottom:4px">'
                              f"{he(_label('h_2_reporter_comments'))}</div>"
                              f'<div class="narrative-block">{he(reporter)}</div></div>')
                if sender:
                    inner += (f'<div style="margin-bottom:10px"><div class="field-label" '
                              f'style="color:#5c6bc0;font-weight:600;margin-bottom:4px">'
                              f"{he(_label('h_4_sender_comments'))}</div>"
                              f'<div class="narrative-block">{he(sender)}</div></div>')
                rest = {k: v for k, v in val.items()
                        if k not in ('h_1_case_narrative', 'h_2_reporter_comments', 'h_4_sender_comments')}
                inner += _render_obj(rest)
                content = f'<div class="section-body">{inner}</div>'
            else:
                inner = _render_obj(val)
                content = f'<div class="section-body">{inner}</div>'

        body_parts.append(
            f'<div class="section">'
            f'<div class="section-title">{he(title)}</div>'
            f'{content}</div>'
        )

    body_html = ''.join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ICSR Report — {he(case_id)}</title>
  {_HTML_CSS}
</head>
<body>
  <div class="report-wrapper">
    {header}
    <div class="report-body">
      {body_html}
    </div>
    <div class="report-footer">
      Generated by E2B R3 Import/Export Module v{__version__} &nbsp;|&nbsp;
      ICH E2B(R3) Standard &nbsp;|&nbsp; License: GPL v3
    </div>
  </div>
</body>
</html>"""


# SQL Generator
_SQL_DDL = """-- ============================================================
-- E2B R3 ICSR Database Schema  (SQLite / PostgreSQL compatible)
-- Generated by E2B R3 Import/Export Module v{version}
-- Standard: ICH E2B(R3)  |  License: GPL v3
-- ============================================================

CREATE TABLE IF NOT EXISTS icsr (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_at TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS c1_identification (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id                         INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    sender_safety_report_unique_id  TEXT,
    date_creation                   TEXT,
    type_report                     TEXT,
    date_first_received             TEXT,
    date_most_recent                TEXT,
    additional_documents_available  TEXT,
    fulfil_local_criteria           TEXT,
    worldwide_unique_case_id        TEXT,
    first_sender                    TEXT,
    other_case_ids_previous         TEXT,
    report_nullification_amendment  TEXT,
    reason_nullification_amendment  TEXT
);

CREATE TABLE IF NOT EXISTS c1_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    c1_id           INTEGER REFERENCES c1_identification(id) ON DELETE CASCADE,
    document_name   TEXT
);

CREATE TABLE IF NOT EXISTS c1_source_case_ids (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    c1_id       INTEGER REFERENCES c1_identification(id) ON DELETE CASCADE,
    source      TEXT,
    case_id     TEXT
);

CREATE TABLE IF NOT EXISTS c1_linked_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    c1_id           INTEGER REFERENCES c1_identification(id) ON DELETE CASCADE,
    report_number   TEXT
);

CREATE TABLE IF NOT EXISTS c2_primary_sources (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id                     INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    reporter_title              TEXT,
    reporter_given_name         TEXT,
    reporter_middle_name        TEXT,
    reporter_family_name        TEXT,
    reporter_organisation       TEXT,
    reporter_department         TEXT,
    reporter_street             TEXT,
    reporter_city               TEXT,
    reporter_state              TEXT,
    reporter_postcode           TEXT,
    reporter_telephone          TEXT,
    reporter_country_code       TEXT,
    qualification               TEXT,
    primary_source_regulatory   TEXT
);

CREATE TABLE IF NOT EXISTS c3_sender (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id                 INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    sender_type             TEXT,
    sender_organisation     TEXT,
    sender_department       TEXT,
    sender_title            TEXT,
    sender_given_name       TEXT,
    sender_middle_name      TEXT,
    sender_family_name      TEXT,
    sender_street           TEXT,
    sender_city             TEXT,
    sender_state            TEXT,
    sender_postcode         TEXT,
    sender_country_code     TEXT,
    sender_telephone        TEXT,
    sender_fax              TEXT,
    sender_email            TEXT
);

CREATE TABLE IF NOT EXISTS c4_literature (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id             INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    literature_reference TEXT
);

CREATE TABLE IF NOT EXISTS c5_study (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id             INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    study_name          TEXT,
    sponsor_study_number TEXT,
    study_type          TEXT
);

CREATE TABLE IF NOT EXISTS c5_study_registrations (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    c5_id                       INTEGER REFERENCES c5_study(id) ON DELETE CASCADE,
    registration_number         TEXT,
    registration_country        TEXT
);

CREATE TABLE IF NOT EXISTS d_patient (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id                         INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    patient_initials                TEXT,
    medical_record_gp               TEXT,
    medical_record_specialist       TEXT,
    medical_record_hospital         TEXT,
    medical_record_investigation    TEXT,
    date_birth                      TEXT,
    age_onset_num                   TEXT,
    age_onset_unit                  TEXT,
    gestation_period_num            TEXT,
    gestation_period_unit           TEXT,
    age_group                       TEXT,
    body_weight_kg                  TEXT,
    height_cm                       TEXT,
    sex                             TEXT,
    last_menstrual_period           TEXT,
    text_medical_history            TEXT,
    concomitant_therapies           TEXT,
    date_death                      TEXT,
    autopsy_done                    TEXT,
    parent_identification           TEXT,
    parent_date_birth               TEXT,
    parent_age_num                  TEXT,
    parent_age_unit                 TEXT,
    parent_last_menstrual_period    TEXT,
    parent_body_weight_kg           TEXT,
    parent_height_cm                TEXT,
    parent_sex                      TEXT,
    parent_text_medical_history     TEXT
);

CREATE TABLE IF NOT EXISTS d_medical_history (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                  INTEGER REFERENCES d_patient(id) ON DELETE CASCADE,
    meddra_version              TEXT,
    meddra_code                 TEXT,
    start_date                  TEXT,
    continuing                  TEXT,
    end_date                    TEXT,
    comments                    TEXT,
    family_history              TEXT
);

CREATE TABLE IF NOT EXISTS d_past_drugs (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                  INTEGER REFERENCES d_patient(id) ON DELETE CASCADE,
    drug_name                   TEXT,
    mpid_version                TEXT,
    mpid                        TEXT,
    phpid_version               TEXT,
    phpid                       TEXT,
    start_date                  TEXT,
    end_date                    TEXT,
    indication_meddra_version   TEXT,
    indication_meddra_code      TEXT,
    reaction_meddra_version     TEXT,
    reaction_meddra_code        TEXT
);

CREATE TABLE IF NOT EXISTS d_cause_death (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER REFERENCES d_patient(id) ON DELETE CASCADE,
    meddra_version  TEXT,
    meddra_code     TEXT,
    cause_text      TEXT
);

CREATE TABLE IF NOT EXISTS d_autopsy_cause (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER REFERENCES d_patient(id) ON DELETE CASCADE,
    meddra_version  TEXT,
    meddra_code     TEXT,
    cause_text      TEXT
);

CREATE TABLE IF NOT EXISTS e_reactions (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id                         INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    reaction_native_language        TEXT,
    reaction_language               TEXT,
    reaction_translation            TEXT,
    meddra_version                  TEXT,
    meddra_code                     TEXT,
    term_highlighted                TEXT,
    seriousness_death               TEXT,
    seriousness_life_threatening    TEXT,
    seriousness_hospitalisation     TEXT,
    seriousness_disabling           TEXT,
    seriousness_congenital          TEXT,
    seriousness_other               TEXT,
    date_start                      TEXT,
    date_end                        TEXT,
    duration_num                    TEXT,
    duration_unit                   TEXT,
    outcome                         TEXT,
    medical_confirmation            TEXT,
    country                         TEXT
);

CREATE TABLE IF NOT EXISTS f_tests (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id             INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    test_date           TEXT,
    test_name           TEXT,
    meddra_version      TEXT,
    meddra_code         TEXT,
    result_code         TEXT,
    result_value        TEXT,
    result_unit         TEXT,
    result_unstructured TEXT,
    normal_low          TEXT,
    normal_high         TEXT,
    comments            TEXT,
    more_info_available TEXT
);

CREATE TABLE IF NOT EXISTS g_drugs (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id                     INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    drug_role                   TEXT,
    mpid_version                TEXT,
    mpid                        TEXT,
    phpid_version               TEXT,
    phpid                       TEXT,
    product_name                TEXT,
    country_obtained            TEXT,
    investigational_blinded     TEXT,
    authorisation_number        TEXT,
    authorisation_country       TEXT,
    holder_name                 TEXT,
    cumulative_dose_num         TEXT,
    cumulative_dose_unit        TEXT,
    gestation_period_num        TEXT,
    gestation_period_unit       TEXT,
    action_taken                TEXT,
    additional_info_text        TEXT
);

CREATE TABLE IF NOT EXISTS g_substances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id         INTEGER REFERENCES g_drugs(id) ON DELETE CASCADE,
    substance_name  TEXT,
    termid_version  TEXT,
    termid          TEXT,
    strength_num    TEXT,
    strength_unit   TEXT
);

CREATE TABLE IF NOT EXISTS g_dosages (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id                     INTEGER REFERENCES g_drugs(id) ON DELETE CASCADE,
    dose_num                    TEXT,
    dose_unit                   TEXT,
    number_units_interval       TEXT,
    interval_unit               TEXT,
    date_start                  TEXT,
    date_last_admin             TEXT,
    duration_num                TEXT,
    duration_unit               TEXT,
    batch_lot_number            TEXT,
    dosage_text                 TEXT,
    dose_form                   TEXT,
    route_administration        TEXT,
    parent_route_administration TEXT
);

CREATE TABLE IF NOT EXISTS g_indications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id             INTEGER REFERENCES g_drugs(id) ON DELETE CASCADE,
    indication_text     TEXT,
    meddra_version      TEXT,
    meddra_code         TEXT
);

CREATE TABLE IF NOT EXISTS g_reaction_matrix (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id                     INTEGER REFERENCES g_drugs(id) ON DELETE CASCADE,
    reaction_index              TEXT,
    interval_admin_reaction_num TEXT,
    interval_admin_reaction_unit TEXT,
    interval_last_dose_num      TEXT,
    interval_last_dose_unit     TEXT,
    recur_readministration      TEXT
);

CREATE TABLE IF NOT EXISTS g_assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    matrix_id       INTEGER REFERENCES g_reaction_matrix(id) ON DELETE CASCADE,
    source          TEXT,
    method          TEXT,
    result          TEXT
);

CREATE TABLE IF NOT EXISTS g_additional_info (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id     INTEGER REFERENCES g_drugs(id) ON DELETE CASCADE,
    info_code   TEXT
);

CREATE TABLE IF NOT EXISTS h_narrative (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    icsr_id             INTEGER REFERENCES icsr(id) ON DELETE CASCADE,
    case_narrative      TEXT,
    reporter_comments   TEXT,
    sender_comments     TEXT
);

CREATE TABLE IF NOT EXISTS h_sender_diagnosis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    narrative_id    INTEGER REFERENCES h_narrative(id) ON DELETE CASCADE,
    meddra_version  TEXT,
    meddra_code     TEXT
);

CREATE TABLE IF NOT EXISTS h_reporter_comments_native (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    narrative_id    INTEGER REFERENCES h_narrative(id) ON DELETE CASCADE,
    comments_text   TEXT,
    language        TEXT
);
"""


def _sq(v: Any) -> str:
    """Escape a value for SQL single-quoted string."""
    if v is None:
        return 'NULL'
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _sv(raw: Any, field: str = '') -> str:
    """Get SQL-safe string for a raw parsed value."""
    if raw is None:
        return 'NULL'
    if isinstance(raw, dict):
        nf = raw.get('_null_flavor')
        if nf:
            return _sq(f'[{NULL_FLAVOR_LABELS.get(nf, nf)}]')
        v = raw.get('_value')
        return _sq(v) if v is not None else 'NULL'
    return _sq(str(raw))


def _insert(table: str, col_val: Dict[str, Any]) -> str:
    cols = ', '.join(col_val.keys())
    vals = ', '.join(str(v) for v in col_val.values())
    return f'INSERT INTO {table} ({cols}) VALUES ({vals});'


def _to_sql(data: Dict[str, Any], root_tag: str, dialect: str = 'sqlite',
            include_ddl: bool = True) -> str:
    lines: List[str] = []

    if include_ddl:
        ddl = _SQL_DDL.format(version=__version__)
        if dialect == 'postgresql':
            ddl = ddl.replace('INTEGER PRIMARY KEY AUTOINCREMENT',
                              'SERIAL PRIMARY KEY')
        lines.append(ddl)

    lines.append(f'\n-- Data exported from {root_tag}\n')
    lines.append(_insert('icsr', {}))
    lines.append('-- (icsr row uses auto-generated id=1 below)\n')

    icsr_id = 1

    # C.1
    c1 = data.get('c_1_identification_case_safety_report') or {}
    if c1:
        c1_row = {
            'icsr_id':                         icsr_id,
            'sender_safety_report_unique_id':  _sv(c1.get('c_1_1_sender_safety_report_unique_id')),
            'date_creation':                   _sv(c1.get('c_1_2_date_creation')),
            'type_report':                     _sv(c1.get('c_1_3_type_report')),
            'date_first_received':             _sv(c1.get('c_1_4_date_report_first_received_source')),
            'date_most_recent':                _sv(c1.get('c_1_5_date_most_recent_information')),
            'additional_documents_available':  _sv(c1.get('c_1_6_1_additional_documents_available')),
            'fulfil_local_criteria':           _sv(c1.get('c_1_7_fulfil_local_criteria_expedited_report')),
            'worldwide_unique_case_id':        _sv(c1.get('c_1_8_1_worldwide_unique_case_identification_number')),
            'first_sender':                    _sv(c1.get('c_1_8_2_first_sender')),
            'other_case_ids_previous':         _sv(c1.get('c_1_9_1_other_case_ids_previous_transmissions')),
            'report_nullification_amendment':  _sv(c1.get('c_1_11_1_report_nullification_amendment')),
            'reason_nullification_amendment':  _sv(c1.get('c_1_11_2_reason_nullification_amendment')),
        }
        lines.append(_insert('c1_identification', c1_row))
        c1_id = 1

        for doc in (c1.get('c_1_6_1_r_documents_held_sender') or []):
            lines.append(_insert('c1_documents', {
                'c1_id': c1_id,
                'document_name': _sv(doc.get('c_1_6_1_r_1_documents_held_sender') if isinstance(doc, dict) else doc),
            }))

        for src in (c1.get('c_1_9_1_r_source_case_id') or []):
            if isinstance(src, dict):
                lines.append(_insert('c1_source_case_ids', {
                    'c1_id':   c1_id,
                    'source':  _sv(src.get('c_1_9_1_r_1_source_case_id')),
                    'case_id': _sv(src.get('c_1_9_1_r_2_case_id')),
                }))

        for lnk in (c1.get('c_1_10_r_identification_number_report_linked') or []):
            lines.append(_insert('c1_linked_reports', {
                'c1_id':         c1_id,
                'report_number': _sv(lnk.get('c_1_10_r_identification_number_report_linked')
                                     if isinstance(lnk, dict) else lnk),
            }))

    # C.2
    for src in (data.get('c_2_r_primary_source_information') or []):
        if not isinstance(src, dict):
            continue
        lines.append(_insert('c2_primary_sources', {
            'icsr_id':                    icsr_id,
            'reporter_title':             _sv(src.get('c_2_r_1_1_reporter_title')),
            'reporter_given_name':        _sv(src.get('c_2_r_1_2_reporter_given_name')),
            'reporter_middle_name':       _sv(src.get('c_2_r_1_3_reporter_middle_name')),
            'reporter_family_name':       _sv(src.get('c_2_r_1_4_reporter_family_name')),
            'reporter_organisation':      _sv(src.get('c_2_r_2_1_reporter_organisation')),
            'reporter_department':        _sv(src.get('c_2_r_2_2_reporter_department')),
            'reporter_street':            _sv(src.get('c_2_r_2_3_reporter_street')),
            'reporter_city':              _sv(src.get('c_2_r_2_4_reporter_city')),
            'reporter_state':             _sv(src.get('c_2_r_2_5_reporter_state_province')),
            'reporter_postcode':          _sv(src.get('c_2_r_2_6_reporter_postcode')),
            'reporter_telephone':         _sv(src.get('c_2_r_2_7_reporter_telephone')),
            'reporter_country_code':      _sv(src.get('c_2_r_3_reporter_country_code')),
            'qualification':              _sv(src.get('c_2_r_4_qualification')),
            'primary_source_regulatory':  _sv(src.get('c_2_r_5_primary_source_regulatory_purposes')),
        }))

    # C.3
    c3 = data.get('c_3_information_sender_case_safety_report') or {}
    if c3:
        lines.append(_insert('c3_sender', {
            'icsr_id':             icsr_id,
            'sender_type':         _sv(c3.get('c_3_1_sender_type')),
            'sender_organisation': _sv(c3.get('c_3_2_sender_organisation')),
            'sender_department':   _sv(c3.get('c_3_3_1_sender_department')),
            'sender_title':        _sv(c3.get('c_3_3_2_sender_title')),
            'sender_given_name':   _sv(c3.get('c_3_3_3_sender_given_name')),
            'sender_middle_name':  _sv(c3.get('c_3_3_4_sender_middle_name')),
            'sender_family_name':  _sv(c3.get('c_3_3_5_sender_family_name')),
            'sender_street':       _sv(c3.get('c_3_4_1_sender_street_address')),
            'sender_city':         _sv(c3.get('c_3_4_2_sender_city')),
            'sender_state':        _sv(c3.get('c_3_4_3_sender_state_province')),
            'sender_postcode':     _sv(c3.get('c_3_4_4_sender_postcode')),
            'sender_country_code': _sv(c3.get('c_3_4_5_sender_country_code')),
            'sender_telephone':    _sv(c3.get('c_3_4_6_sender_telephone')),
            'sender_fax':          _sv(c3.get('c_3_4_7_sender_fax')),
            'sender_email':        _sv(c3.get('c_3_4_8_sender_email')),
        }))

    # C.4
    for lit in (data.get('c_4_r_literature_reference') or []):
        if isinstance(lit, dict):
            ref = _sv(lit.get('c_4_r_1_literature_reference'))
        else:
            ref = _sq(str(lit))
        lines.append(_insert('c4_literature', {'icsr_id': icsr_id, 'literature_reference': ref}))

    # C.5
    c5 = data.get('c_5_study_identification') or {}
    if c5:
        lines.append(_insert('c5_study', {
            'icsr_id':              icsr_id,
            'study_name':           _sv(c5.get('c_5_2_study_name')),
            'sponsor_study_number': _sv(c5.get('c_5_3_sponsor_study_number')),
            'study_type':           _sv(c5.get('c_5_4_study_type_reaction')),
        }))
        c5_id = 1
        for reg in (c5.get('c_5_1_r_study_registration') or []):
            if isinstance(reg, dict):
                lines.append(_insert('c5_study_registrations', {
                    'c5_id':                1,
                    'registration_number':  _sv(reg.get('c_5_1_r_1_study_registration_number')),
                    'registration_country': _sv(reg.get('c_5_1_r_2_study_registration_country')),
                }))

    # ----- D -----
    d = data.get('d_patient_characteristics') or {}
    if d:
        lines.append(_insert('d_patient', {
            'icsr_id':                      icsr_id,
            'patient_initials':             _sv(d.get('d_1_patient')),
            'medical_record_gp':            _sv(d.get('d_1_1_1_medical_record_number_source_gp')),
            'medical_record_specialist':    _sv(d.get('d_1_1_2_medical_record_number_source_specialist')),
            'medical_record_hospital':      _sv(d.get('d_1_1_3_medical_record_number_source_hospital')),
            'medical_record_investigation': _sv(d.get('d_1_1_4_medical_record_number_source_investigation')),
            'date_birth':                   _sv(d.get('d_2_1_date_birth')),
            'age_onset_num':                _sv(d.get('d_2_2a_age_onset_reaction_num')),
            'age_onset_unit':               _sv(d.get('d_2_2b_age_onset_reaction_unit')),
            'gestation_period_num':         _sv(d.get('d_2_2_1a_gestation_period_reaction_foetus_num')),
            'gestation_period_unit':        _sv(d.get('d_2_2_1b_gestation_period_reaction_foetus_unit')),
            'age_group':                    _sv(d.get('d_2_3_patient_age_group')),
            'body_weight_kg':               _sv(d.get('d_3_body_weight')),
            'height_cm':                    _sv(d.get('d_4_height')),
            'sex':                          _sv(d.get('d_5_sex')),
            'last_menstrual_period':        _sv(d.get('d_6_last_menstrual_period_date')),
            'text_medical_history':         _sv(d.get('d_7_2_text_medical_history')),
            'concomitant_therapies':        _sv(d.get('d_7_3_concomitant_therapies')),
            'date_death':                   _sv(d.get('d_9_1_date_death')),
            'autopsy_done':                 _sv(d.get('d_9_3_autopsy')),
            'parent_identification':        _sv(d.get('d_10_1_parent_identification')),
            'parent_date_birth':            _sv(d.get('d_10_2_1_date_birth_parent')),
            'parent_age_num':               _sv(d.get('d_10_2_2a_age_parent_num')),
            'parent_age_unit':              _sv(d.get('d_10_2_2b_age_parent_unit')),
            'parent_last_menstrual_period': _sv(d.get('d_10_3_last_menstrual_period_date_parent')),
            'parent_body_weight_kg':        _sv(d.get('d_10_4_body_weight_parent')),
            'parent_height_cm':             _sv(d.get('d_10_5_height_parent')),
            'parent_sex':                   _sv(d.get('d_10_6_sex_parent')),
            'parent_text_medical_history':  _sv(d.get('d_10_7_2_text_medical_history_parent')),
        }))
        pat_id = 1

        for mh in (d.get('d_7_1_r_structured_information_medical_history') or []):
            if isinstance(mh, dict):
                lines.append(_insert('d_medical_history', {
                    'patient_id':    pat_id,
                    'meddra_version': _sv(mh.get('d_7_1_r_1a_meddra_version_medical_history')),
                    'meddra_code':    _sv(mh.get('d_7_1_r_1b_medical_history_meddra_code')),
                    'start_date':     _sv(mh.get('d_7_1_r_2_start_date')),
                    'continuing':     _sv(mh.get('d_7_1_r_3_continuing')),
                    'end_date':       _sv(mh.get('d_7_1_r_4_end_date')),
                    'comments':       _sv(mh.get('d_7_1_r_5_comments')),
                    'family_history': _sv(mh.get('d_7_1_r_6_family_history')),
                }))

        for pd in (d.get('d_8_r_past_drug_history') or []):
            if isinstance(pd, dict):
                lines.append(_insert('d_past_drugs', {
                    'patient_id':               pat_id,
                    'drug_name':                _sv(pd.get('d_8_r_1_name_drug')),
                    'mpid_version':             _sv(pd.get('d_8_r_2a_mpid_version')),
                    'mpid':                     _sv(pd.get('d_8_r_2b_mpid')),
                    'phpid_version':            _sv(pd.get('d_8_r_3a_phpid_version')),
                    'phpid':                    _sv(pd.get('d_8_r_3b_phpid')),
                    'start_date':               _sv(pd.get('d_8_r_4_start_date')),
                    'end_date':                 _sv(pd.get('d_8_r_5_end_date')),
                    'indication_meddra_version':_sv(pd.get('d_8_r_6a_meddra_version_indication')),
                    'indication_meddra_code':   _sv(pd.get('d_8_r_6b_indication_meddra_code')),
                    'reaction_meddra_version':  _sv(pd.get('d_8_r_7a_meddra_version_reaction')),
                    'reaction_meddra_code':     _sv(pd.get('d_8_r_7b_reaction_meddra_code')),
                }))

        for cd in (d.get('d_9_2_r_cause_death') or []):
            if isinstance(cd, dict):
                lines.append(_insert('d_cause_death', {
                    'patient_id':    pat_id,
                    'meddra_version': _sv(cd.get('d_9_2_r_1a_meddra_version_cause_death')),
                    'meddra_code':    _sv(cd.get('d_9_2_r_1b_cause_death_meddra_code')),
                    'cause_text':     _sv(cd.get('d_9_2_r_2_cause_death')),
                }))

        for ac in (d.get('d_9_4_r_autopsy_determined_cause_death') or []):
            if isinstance(ac, dict):
                lines.append(_insert('d_autopsy_cause', {
                    'patient_id':    pat_id,
                    'meddra_version': _sv(ac.get('d_9_4_r_1a_meddra_version_autopsy_determined_cause_death')),
                    'meddra_code':    _sv(ac.get('d_9_4_r_1b_autopsy_determined_cause_death_meddra_code')),
                    'cause_text':     _sv(ac.get('d_9_4_r_2_autopsy_determined_cause_death')),
                }))

    # ----- E -----
    for rx in (data.get('e_i_reaction_event') or []):
        if not isinstance(rx, dict):
            continue
        lines.append(_insert('e_reactions', {
            'icsr_id':                        icsr_id,
            'reaction_native_language':       _sv(rx.get('e_i_1_1a_reaction_primary_source_native_language')),
            'reaction_language':              _sv(rx.get('e_i_1_1b_reaction_primary_source_language')),
            'reaction_translation':           _sv(rx.get('e_i_1_2_reaction_primary_source_translation')),
            'meddra_version':                 _sv(rx.get('e_i_2_1a_meddra_version_reaction')),
            'meddra_code':                    _sv(rx.get('e_i_2_1b_reaction_meddra_code')),
            'term_highlighted':               _sv(rx.get('e_i_3_1_term_highlighted_reporter')),
            'seriousness_death':              _sv(rx.get('e_i_3_2a_results_death')),
            'seriousness_life_threatening':   _sv(rx.get('e_i_3_2b_life_threatening')),
            'seriousness_hospitalisation':    _sv(rx.get('e_i_3_2c_caused_prolonged_hospitalisation')),
            'seriousness_disabling':          _sv(rx.get('e_i_3_2d_disabling_incapacitating')),
            'seriousness_congenital':         _sv(rx.get('e_i_3_2e_congenital_anomaly_birth_defect')),
            'seriousness_other':              _sv(rx.get('e_i_3_2f_other_medically_important_condition')),
            'date_start':                     _sv(rx.get('e_i_4_date_start_reaction')),
            'date_end':                       _sv(rx.get('e_i_5_date_end_reaction')),
            'duration_num':                   _sv(rx.get('e_i_6a_duration_reaction_num')),
            'duration_unit':                  _sv(rx.get('e_i_6b_duration_reaction_unit')),
            'outcome':                        _sv(rx.get('e_i_7_outcome_reaction_last_observation')),
            'medical_confirmation':           _sv(rx.get('e_i_8_medical_confirmation_healthcare_professional')),
            'country':                        _sv(rx.get('e_i_9_identification_country_reaction')),
        }))

    # ----- F -----
    for tst in (data.get('f_r_results_tests_procedures_investigation_patient') or []):
        if not isinstance(tst, dict):
            continue
        lines.append(_insert('f_tests', {
            'icsr_id':            icsr_id,
            'test_date':          _sv(tst.get('f_r_1_test_date')),
            'test_name':          _sv(tst.get('f_r_2_1_test_name')),
            'meddra_version':     _sv(tst.get('f_r_2_2a_meddra_version_test_name')),
            'meddra_code':        _sv(tst.get('f_r_2_2b_test_name_meddra_code')),
            'result_code':        _sv(tst.get('f_r_3_1_test_result_code')),
            'result_value':       _sv(tst.get('f_r_3_2_test_result_val_qual')),
            'result_unit':        _sv(tst.get('f_r_3_3_test_result_unit')),
            'result_unstructured':_sv(tst.get('f_r_3_4_result_unstructured_data')),
            'normal_low':         _sv(tst.get('f_r_4_normal_low_value')),
            'normal_high':        _sv(tst.get('f_r_5_normal_high_value')),
            'comments':           _sv(tst.get('f_r_6_comments')),
            'more_info_available':_sv(tst.get('f_r_7_more_information_available')),
        }))

    # ----- G -----
    for drug_idx, drg in enumerate((data.get('g_k_drug_information') or []), 1):
        if not isinstance(drg, dict):
            continue
        lines.append(_insert('g_drugs', {
            'icsr_id':                  icsr_id,
            'drug_role':                _sv(drg.get('g_k_1_characterisation_drug_role')),
            'mpid_version':             _sv(drg.get('g_k_2_1_1a_mpid_version')),
            'mpid':                     _sv(drg.get('g_k_2_1_1b_mpid')),
            'phpid_version':            _sv(drg.get('g_k_2_1_2a_phpid_version')),
            'phpid':                    _sv(drg.get('g_k_2_1_2b_phpid')),
            'product_name':             _sv(drg.get('g_k_2_2_medicinal_product_name_primary_source')),
            'country_obtained':         _sv(drg.get('g_k_2_4_identification_country_drug_obtained')),
            'investigational_blinded':  _sv(drg.get('g_k_2_5_investigational_product_blinded')),
            'authorisation_number':     _sv(drg.get('g_k_3_1_authorisation_application_number')),
            'authorisation_country':    _sv(drg.get('g_k_3_2_country_authorisation_application')),
            'holder_name':              _sv(drg.get('g_k_3_3_name_holder_applicant')),
            'cumulative_dose_num':      _sv(drg.get('g_k_5a_cumulative_dose_first_reaction_num')),
            'cumulative_dose_unit':     _sv(drg.get('g_k_5b_cumulative_dose_first_reaction_unit')),
            'gestation_period_num':     _sv(drg.get('g_k_6a_gestation_period_exposure_num')),
            'gestation_period_unit':    _sv(drg.get('g_k_6b_gestation_period_exposure_unit')),
            'action_taken':             _sv(drg.get('g_k_8_action_taken_drug')),
            'additional_info_text':     _sv(drg.get('g_k_11_additional_information_drug')),
        }))
        drug_sql_id = drug_idx

        for sub in (drg.get('g_k_2_3_r_substance_id_strength') or []):
            if isinstance(sub, dict):
                lines.append(_insert('g_substances', {
                    'drug_id':        drug_sql_id,
                    'substance_name': _sv(sub.get('g_k_2_3_r_1_substance_name')),
                    'termid_version': _sv(sub.get('g_k_2_3_r_2a_substance_termid_version')),
                    'termid':         _sv(sub.get('g_k_2_3_r_2b_substance_termid')),
                    'strength_num':   _sv(sub.get('g_k_2_3_r_3a_strength_num')),
                    'strength_unit':  _sv(sub.get('g_k_2_3_r_3b_strength_unit')),
                }))

        for dos in (drg.get('g_k_4_r_dosage_information') or []):
            if isinstance(dos, dict):
                lines.append(_insert('g_dosages', {
                    'drug_id':                   drug_sql_id,
                    'dose_num':                  _sv(dos.get('g_k_4_r_1a_dose_num')),
                    'dose_unit':                 _sv(dos.get('g_k_4_r_1b_dose_unit')),
                    'number_units_interval':     _sv(dos.get('g_k_4_r_2_number_units_interval')),
                    'interval_unit':             _sv(dos.get('g_k_4_r_3_definition_interval_unit')),
                    'date_start':                _sv(dos.get('g_k_4_r_4_date_time_drug')),
                    'date_last_admin':           _sv(dos.get('g_k_4_r_5_date_time_last_administration')),
                    'duration_num':              _sv(dos.get('g_k_4_r_6a_duration_drug_administration_num')),
                    'duration_unit':             _sv(dos.get('g_k_4_r_6b_duration_drug_administration_unit')),
                    'batch_lot_number':          _sv(dos.get('g_k_4_r_7_batch_lot_number')),
                    'dosage_text':               _sv(dos.get('g_k_4_r_8_dosage_text')),
                    'dose_form':                 _sv(dos.get('g_k_4_r_9_1_pharmaceutical_dose_form')),
                    'route_administration':      _sv(dos.get('g_k_4_r_10_1_route_administration')),
                    'parent_route_administration': _sv(dos.get('g_k_4_r_11_1_parent_route_administration')),
                }))

        for ind in (drg.get('g_k_7_r_indication_use_case') or []):
            if isinstance(ind, dict):
                lines.append(_insert('g_indications', {
                    'drug_id':        drug_sql_id,
                    'indication_text': _sv(ind.get('g_k_7_r_1_indication_primary_source')),
                    'meddra_version':  _sv(ind.get('g_k_7_r_2a_meddra_version_indication')),
                    'meddra_code':     _sv(ind.get('g_k_7_r_2b_indication_meddra_code')),
                }))

        for matrix_idx, mx in enumerate((drg.get('g_k_9_i_drug_reaction_matrix') or []), 1):
            if isinstance(mx, dict):
                lines.append(_insert('g_reaction_matrix', {
                    'drug_id':                      drug_sql_id,
                    'reaction_index':               _sq(str(mx.get('g_k_9_i_1_reaction_assessed', ''))),
                    'interval_admin_reaction_num':  _sv(mx.get('g_k_9_i_3_1a_interval_drug_administration_reaction_num')),
                    'interval_admin_reaction_unit': _sv(mx.get('g_k_9_i_3_1b_interval_drug_administration_reaction_unit')),
                    'interval_last_dose_num':       _sv(mx.get('g_k_9_i_3_2a_interval_last_dose_drug_reaction_num')),
                    'interval_last_dose_unit':      _sv(mx.get('g_k_9_i_3_2b_interval_last_dose_drug_reaction_unit')),
                    'recur_readministration':       _sv(mx.get('g_k_9_i_4_reaction_recur_readministration')),
                }))
                matrix_sql_id = matrix_idx
                for asmnt in (mx.get('g_k_9_i_2_r_assessment_relatedness_drug_reaction') or []):
                    if isinstance(asmnt, dict):
                        lines.append(_insert('g_assessments', {
                            'matrix_id': matrix_sql_id,
                            'source':    _sv(asmnt.get('g_k_9_i_2_r_1_source_assessment')),
                            'method':    _sv(asmnt.get('g_k_9_i_2_r_2_method_assessment')),
                            'result':    _sv(asmnt.get('g_k_9_i_2_r_3_result_assessment')),
                        }))

        for ai in (drg.get('g_k_10_r_additional_information_drug') or []):
            val = ai.get('g_k_10_r_additional_information_drug') if isinstance(ai, dict) else ai
            lines.append(_insert('g_additional_info', {
                'drug_id':   drug_sql_id,
                'info_code': _sv(val),
            }))

    # H
    h = data.get('h_narrative_case_summary') or {}
    if h:
        lines.append(_insert('h_narrative', {
            'icsr_id':            icsr_id,
            'case_narrative':     _sv(h.get('h_1_case_narrative')),
            'reporter_comments':  _sv(h.get('h_2_reporter_comments')),
            'sender_comments':    _sv(h.get('h_4_sender_comments')),
        }))
        narr_id = 1

        for diag in (h.get('h_3_r_sender_diagnosis_meddra_code') or []):
            if isinstance(diag, dict):
                lines.append(_insert('h_sender_diagnosis', {
                    'narrative_id':  narr_id,
                    'meddra_version': _sv(diag.get('h_3_r_1a_meddra_version_sender_diagnosis')),
                    'meddra_code':    _sv(diag.get('h_3_r_1b_sender_diagnosis_meddra_code')),
                }))

        for cmt in (h.get('h_5_r_case_summary_reporter_comments_native_language') or []):
            if isinstance(cmt, dict):
                lines.append(_insert('h_reporter_comments_native', {
                    'narrative_id':  narr_id,
                    'comments_text': _sv(cmt.get('h_5_r_1a_case_summary_reporter_comments_text')),
                    'language':      _sv(cmt.get('h_5_r_1b_case_summary_reporter_comments_language')),
                }))

    return '\n'.join(lines)


# XML Generator  (dict → XML)
def _dict_to_xml_elem(tag: str, value: Any, parent: Optional[ET.Element] = None) -> ET.Element:
    """Recursively build an ElementTree element from a value."""
    elem = ET.SubElement(parent, tag) if parent is not None else ET.Element(tag)

    if value is None:
        return elem

    if isinstance(value, dict):
        if 'null_flavor' in value or 'value' in value:
            val_elem = ET.SubElement(elem, 'value')
            v = value.get('value')
            if v is not None:
                val_elem.text = str(v)
            nf = value.get('null_flavor')
            if nf:
                nf_elem = ET.SubElement(elem, 'null_flavor')
                nf_elem.text = str(nf)
        else:
            for k, v in value.items():
                if isinstance(v, list):
                    for item in v:
                        _dict_to_xml_elem(k, item, elem)
                    if len(v) == 1:
                        ET.SubElement(elem, k)
                else:
                    _dict_to_xml_elem(k, v, elem)
        return elem

    if isinstance(value, list):
        for item in value:
            _dict_to_xml_elem(tag, item, parent)
        return elem

    val_elem = ET.SubElement(elem, 'value')
    val_elem.text = str(value)
    return elem


def _to_xml(data: Any, root_tag: str) -> str:
    """Convert dict (from JSON) back to E2B R3 application XML."""
    root = ET.Element(root_tag)
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                for item in val:
                    _dict_to_xml_elem(key, item, root)
                if len(val) == 1:
                    ET.SubElement(root, key)
            else:
                _dict_to_xml_elem(key, val, root)
    ET.indent(root, space='  ')
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode')


# Main Converter Class

class E2BConverter:
    """
    Converter for E2B R3 Individual Case Safety Report (ICSR) data.

    Supported conversions:
        XML  → JSON  (xml_to_json)
        XML  → HTML  (xml_to_html)
        XML  → SQL   (xml_to_sql)
        JSON → XML   (json_to_xml)

    File helpers:
        save_as_json, save_as_html, save_as_sql
        load_xml_file, load_json_file
    """

    #  Core converters                                                     #
    @staticmethod
    def xml_to_dict(xml_string: str) -> Dict[str, Any]:
        """Parse E2B R3 XML to a Python dict."""
        _, data = _parse_xml(xml_string)
        return data

    @staticmethod
    def xml_to_json(xml_string: str, indent: int = 2,
                    include_empty: bool = False) -> str:
        """
        Convert E2B R3 XML to a clean JSON string.

        Args:
            xml_string:    Raw XML text.
            indent:        JSON indentation level (default 2).
            include_empty: If True, include null/empty fields in output.

        Returns:
            JSON string.
        """
        root_tag, data = _parse_xml(xml_string)
        return _to_json(data, root_tag, indent=indent, include_empty=include_empty)

    @staticmethod
    def xml_to_html(xml_string: str) -> str:
        """
        Convert E2B R3 XML to a styled HTML report.

        Args:
            xml_string: Raw XML text.

        Returns:
            Complete HTML document as string.
        """
        root_tag, data = _parse_xml(xml_string)
        return _to_html(data, root_tag)

    @staticmethod
    def xml_to_sql(xml_string: str, dialect: str = 'sqlite',
                   include_ddl: bool = True) -> str:
        """
        Convert E2B R3 XML to SQL statements.

        Args:
            xml_string:  Raw XML text.
            dialect:     'sqlite' (default) or 'postgresql'.
            include_ddl: Prepend CREATE TABLE statements (default True).

        Returns:
            SQL text with DDL and INSERT statements.
        """
        root_tag, data = _parse_xml(xml_string)
        return _to_sql(data, root_tag, dialect=dialect, include_ddl=include_ddl)

    @staticmethod
    def json_to_xml(json_string: str) -> str:
        """
        Convert a JSON string (previously exported by xml_to_json) back to
        E2B R3 application XML.

        Args:
            json_string: JSON text produced by xml_to_json.

        Returns:
            XML string.
        """
        obj = json.loads(json_string)
        if not isinstance(obj, dict) or len(obj) != 1:
            raise ValueError('JSON must be a single-key object {root_tag: {...}}')
        root_tag, data = next(iter(obj.items()))
        return _to_xml(data, root_tag)

    #  File helpers                                                        #
    @staticmethod
    def load_xml_file(path: str) -> Dict[str, Any]:
        """Load and parse an E2B R3 XML file, returning a Python dict."""
        with open(path, encoding='utf-8') as f:
            return E2BConverter.xml_to_dict(f.read())

    @staticmethod
    def load_json_file(path: str) -> Dict[str, Any]:
        """Load an exported JSON file, returning a Python dict."""
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save_as_json(xml_string: str, output_path: str,
                     indent: int = 2, include_empty: bool = False) -> None:
        """Convert XML and write JSON to *output_path*."""
        result = E2BConverter.xml_to_json(xml_string, indent=indent,
                                          include_empty=include_empty)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)

    @staticmethod
    def save_as_html(xml_string: str, output_path: str) -> None:
        """Convert XML and write HTML report to *output_path*."""
        result = E2BConverter.xml_to_html(xml_string)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)

    @staticmethod
    def save_as_sql(xml_string: str, output_path: str,
                    dialect: str = 'sqlite', include_ddl: bool = True) -> None:
        """Convert XML and write SQL to *output_path*."""
        result = E2BConverter.xml_to_sql(xml_string, dialect=dialect,
                                         include_ddl=include_ddl)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)

    @staticmethod
    def convert_file(input_path: str, output_format: str,
                     output_path: Optional[str] = None, **kwargs) -> str:
        """
        Convenience: read *input_path* (XML or JSON) and convert.

        Args:
            input_path:    Path to source file (.xml or .json).
            output_format: One of 'json', 'html', 'sql', 'xml'.
            output_path:   If given, write result to this file as well.
            **kwargs:      Forwarded to the specific converter.

        Returns:
            Converted string.
        """
        with open(input_path, encoding='utf-8') as f:
            content = f.read()

        ext = input_path.rsplit('.', 1)[-1].lower()
        if ext == 'json' and output_format == 'xml':
            result = E2BConverter.json_to_xml(content)
        elif ext in ('xml', 'txt'):
            fmt = output_format.lower()
            if fmt == 'json':
                result = E2BConverter.xml_to_json(content, **kwargs)
            elif fmt == 'html':
                result = E2BConverter.xml_to_html(content)
            elif fmt == 'sql':
                result = E2BConverter.xml_to_sql(content, **kwargs)
            else:
                raise ValueError(f'Unknown output format: {output_format}')
        else:
            raise ValueError(f'Cannot determine conversion for input extension: {ext}')

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)

        return result


# Module-level convenience functions
def xml_to_json(xml_string: str, indent: int = 2) -> str:
    """Convert E2B R3 XML to JSON string."""
    return E2BConverter.xml_to_json(xml_string, indent=indent)


def xml_to_html(xml_string: str) -> str:
    """Convert E2B R3 XML to HTML report."""
    return E2BConverter.xml_to_html(xml_string)


def xml_to_sql(xml_string: str, dialect: str = 'sqlite') -> str:
    """Convert E2B R3 XML to SQL statements."""
    return E2BConverter.xml_to_sql(xml_string, dialect=dialect)


def json_to_xml(json_string: str) -> str:
    """Convert JSON (from xml_to_json) back to E2B R3 XML."""
    return E2BConverter.json_to_xml(json_string)


# Command-line interface
def _cli_main() -> None:
    import argparse
    import sys
    import os

    parser = argparse.ArgumentParser(
        prog='e2b_converter',
        description='E2B R3 ICSR Import/Export Tool — converts XML ↔ JSON/HTML/SQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python e2b_converter.py report.xml --format json -o report.json
  python e2b_converter.py report.xml --format html -o report.html
  python e2b_converter.py report.xml --format sql  -o report.sql
  python e2b_converter.py report.xml --format sql  --dialect postgresql -o report.sql
  python e2b_converter.py report.json --format xml -o report_out.xml
        """
    )
    parser.add_argument('input', help='Input file path (.xml or .json)')
    parser.add_argument('-f', '--format', required=True,
                        choices=['json', 'html', 'sql', 'xml'],
                        help='Output format')
    parser.add_argument('-o', '--output', default=None,
                        help='Output file path (stdout if omitted)')
    parser.add_argument('--dialect', default='sqlite',
                        choices=['sqlite', 'postgresql'],
                        help='SQL dialect (only for --format sql, default: sqlite)')
    parser.add_argument('--include-empty', action='store_true',
                        help='Include empty/null fields in JSON output')
    parser.add_argument('--no-ddl', action='store_true',
                        help='Omit CREATE TABLE statements from SQL output')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f'Error: file not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    with open(args.input, encoding='utf-8') as f:
        content = f.read()

    ext = args.input.rsplit('.', 1)[-1].lower()

    try:
        if args.format == 'json':
            result = E2BConverter.xml_to_json(content, include_empty=args.include_empty)
        elif args.format == 'html':
            result = E2BConverter.xml_to_html(content)
        elif args.format == 'sql':
            result = E2BConverter.xml_to_sql(content, dialect=args.dialect,
                                             include_ddl=not args.no_ddl)
        elif args.format == 'xml':
            if ext != 'json':
                print('Error: --format xml expects a JSON input file', file=sys.stderr)
                sys.exit(1)
            result = E2BConverter.json_to_xml(content)
        else:
            print(f'Error: unknown format {args.format}', file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f'Conversion error: {exc}', file=sys.stderr)
        sys.exit(2)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f'Saved to {args.output}')
    else:
        sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')


if __name__ == '__main__':
    _cli_main()
