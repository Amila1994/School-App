import streamlit as st
import pandas as pd
import json
import io
import time
import warnings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Google API Libraries
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Teacher Multi-Class Portal", layout="wide", page_icon="🏫")

# Google Drive API Scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- භාෂා පරිවර්තන ---
LANG_DICT = {
    "Sinhala": {
        "title": "🏫 ගුරු ප්‍රතිඵල සහ ස්වයංක්‍රීය පෞද්ගලික Cloud සංරක්ෂණ පද්ධතිය",
        "home": "🏠 මුල් පිටුව", "settings": "⚙️ පද්ධති සැකසුම්", "workspace": "📊 පන්ති කාමර", "profiles": "👤 ශිෂ්‍ය විස්තර",
        "class_select": "🎯 වැඩ කිරීමට අවශ්‍ය පන්තිය තෝරන්න:", "add_class": "➕ අලුත් පන්තියක් සාදන්න",
        "sub_manage": "📚 વિෂයයන් කළමනාකරණය", "add_sub": "අලුත් විෂයක් එකතු කරන්න:", "pass_mark": "සමත් ලකුණ:",
        "tab_input": "📝 ලකුණු ඇතුළත් කිරීම", "tab_grades": "📊 ශිෂ්‍ය සාමාර්ථ", "tab_ranks": "🏆 ශ්‍රේණිගත කිරීම් සහ PDF",
        "save_btn": "💾 වෙනස්කම් තහවුරු කර Google Drive වෙත සුරකින්න",
        "pdf_btn": "📥 නිල පන්ති වාර්තාව බාගත කරන්න (A4 PDF)"
    },
    "English": {
        "title": "🏫 Teacher Portal & Personal Cloud Auto-Backup System",
        "home": "🏠 Home", "settings": "⚙️ Settings", "workspace": "📊 Class Workspaces", "profiles": "👤 Student Profiles",
        "class_select": "🎯 Select Class Workspace:", "add_class": "➕ Create New Class Workspace",
        "sub_manage": "📚 Subject Management", "add_sub": "Add New Subject:", "pass_mark": "Pass Mark:",
        "tab_input": "📝 Marks Input", "tab_grades": "📊 Student Grades", "tab_ranks": "🏆 Class Rankings & PDF",
        "save_btn": "💾 Confirm Changes & Save to Google Drive",
        "pdf_btn": "📥 Download Official Class Report (A4 PDF)"
    }
}

# --- Session States ආරම්භ කිරීම ---
if 'user_db' not in st.session_state: st.session_state.user_db = {}
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'gdrive_creds' not in st.session_state: st.session_state.gdrive_creds = {}

# ==========================================
# 🔐 TEACHER SIGN-UP & LOGIN ENGINE
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #1A365D;'>🏫 Teacher Registration & Login</h1>", unsafe_allow_html=True)
    login_tab, signup_tab = st.tabs(["🔒 Teacher Login", "📝 Register New Teacher Account"])
    
    with signup_tab:
        r_email = st.text_input("Create Username / Email:", key="reg_email")
        r_pass = st.text_input("Create Password:", type="password", key="reg_pass")
        if st.button("Register Account", use_container_width=True):
            if r_email and r_pass:
                st.session_state.user_db[r_email] = {"password": r_pass, "data": {}}
                st.success("🎉 Account created successfully! Please switch to Login tab.")
            else: st.error("Please fill all fields.")
            
    with login_tab:
        l_email = st.text_input("Enter Email:", key="log_email")
        l_pass = st.text_input("Enter Password:", type="password", key="log_pass")
        if st.button("Sign In", type="primary", use_container_width=True):
            if l_email in st.session_state.user_db and st.session_state.user_db[l_email]["password"] == l_pass:
                st.session_state.logged_in = True
                st.session_state.current_user = l_email
                
                # ගුරුවරයාගේ පැරණි දත්ත තිබේ නම් ලෝඩ් කරයි
                user_data = st.session_state.user_db[l_email]["data"]
                if user_data:
                    st.session_state.all_classes_data = user_data.get("classes", {})
                    st.session_state.school_info = user_data.get("school_info", {"name": "My School", "exam_type": "1st Term Exam"})
                else:
                    st.session_state.all_classes_data = {
                        "10-A": {"teacher": "Class Teacher", "subjects": {"Mathematics": 35}, "df": pd.DataFrame([["ST001", "Kamal Perera", 85]], columns=["Student ID", "Student Name", "Mathematics"]), "personal_info": {}}
                    }
                    st.session_state.school_info = {"name": "පාසලේ නම ඇතුළත් කරන්න", "exam_type": "1st Term Exam"}
                st.rerun()
            else: st.error("❌ Invalid Email or Password!")
    st.stop()

# --- භාෂාව තෝරාගැනීම ---
selected_lang = st.sidebar.selectbox("🌐 Language:", ["English", "Sinhala"])
L = LANG_DICT[selected_lang]

# ==========================================
# ☁️ GOOGLE DRIVE PERSONAL OAUTH ENGINE
# ==========================================
def get_teacher_drive_service():
    user = st.session_state.current_user
    
    # දැනටමත් ලොග් වී ඇත්නම් පැරණි අවසරය ගනී
    if user in st.session_state.gdrive_creds:
        creds = Credentials.from_authorized_user_info(st.session_state.gdrive_creds[user], SCOPES)
        return build('drive', 'v3', credentials=creds)
        
    # නැතහොත් නව අවසර ලින්ක් එකක් සාදයි (ෆෝන් එක ක්‍රෑෂ් නොවීමට)
    if 'oauth_flow' not in st.session_state:
        st.session_state.oauth_flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', 
            scopes=SCOPES,
            redirect_uri='http://localhost'
        )
    
    auth_url, _ = st.session_state.oauth_flow.authorization_url(prompt='select_account')
    
    st.info("🔗 ඔබගේ පෞද්ගලික Google Drive ගිණුමට දත්ත Auto Backup කිරීම සඳහා පහත ලින්ක් එක ක්ලික් කර අවසර ලබාගන්න:")
    st.markdown(f"[👉 Click Here to Authorize Google Drive]({auth_url})", unsafe_allow_html=True)
    
    # අවසර කේතය ඇතුළත් කිරීමට කොටුවක් පෙන්වයි
    auth_code = st.text_input("Google එකෙන් ලැබුණු Code එක හෝ URL එක මෙතැනට පේස්ට් කරන්න:")
    
    if st.button("🔌 Connect My Google Drive"):
        try:
            if "code=" in auth_code:
                auth_code = auth_code.split("code=")[1].split("&")[0]
            st.session_state.oauth_flow.fetch_token(code=auth_code)
            creds = st.session_state.oauth_flow.credentials
            st.session_state.gdrive_creds[user] = json.loads(creds.to_json())
            st.success("✅ Google Drive එක සාර්ථකව සම්බන්ධ කළා! කරුණාකර නැවත Save බොත්තම ඔබන්න.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"සම්බන්ධතාව අසාර්ථකයි: {str(e)}")
    return None

def save_and_backup():
    # 1. Local Database එක සේව් කරයි
    st.session_state.user_db[st.session_state.current_user]["data"] = {
        "classes": st.session_state.all_classes_data,
        "school_info": st.session_state.school_info
    }
    
    # 2. Google Drive එකට Auto Backup කරයි
    service = get_teacher_drive_service()
    if service is None: return # තවම අවසර දී නැත්නම් නතර වේ
    
    try:
        filename = f"My_School_Backup_{st.session_state.current_user.replace('@','_')}.json"
        backup_payload = {
            "school_info": st.session_state.school_info,
            "classes": {}
        }
        for c_name, c_info in st.session_state.all_classes_data.items():
            backup_payload["classes"][c_name] = {
                "teacher": c_info["teacher"],
                "subjects": c_info["subjects"],
                "df_json": c_info["df"].to_json(orient='split'),
                "personal_info": c_info["personal_info"]
            }
            
        json_data = json.dumps(backup_payload)
        media = MediaIoBaseUpload(io.BytesIO(json_data.encode()), mimeType='application/json', resumable=True)
        
        query = f"name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        if items:
            service.files().update(fileId=items[0]['id'], media_body=media).execute()
            st.toast("🔄 Google Drive: Backup Updated Successfully!", icon="☁️")
        else:
            file_metadata = {'name': filename, 'mimeType': 'application/json'}
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            st.toast("🚀 Google Drive: Initial Backup Created!", icon="☁️")
    except Exception as e:
        st.error(f"Cloud Backup Error: {str(e)}")

# ==========================================
# 📊 MAIN WORKSPACE UI
# ==========================================
st.title(L["title"])
st.caption(f"👤 Active Teacher: {st.session_state.current_user} | [🔴 Log Out]")

main_tabs = st.tabs([L["home"], L["settings"], L["workspace"]])

with main_tabs[0]:
    st.subheader(f"🏫 Welcome, {st.session_state.current_user}")
    st.markdown("මෙම පද්ධතිය මඟින් ඔබ ඇතුළත් කරන සියලුම ලකුණු විස්තර ඔබගේම පෞද්ගලික Google Drive ගිණුම තුළ ඉතාමත් සුරක්ෂිතව තැන්පත් කරනු ලබයි.")

with main_tabs[1]:
    st.subheader(L["settings"])
    st.session_state.school_info['name'] = st.text_input("School Name:", st.session_state.school_info['name'])
    
    st.write("---")
    st.markdown("### ☁️ Manual Google Drive Sync")
    if st.button("📥 Load Existing Data From My Personal Google Drive", use_container_width=True):
        service = get_teacher_drive_service()
        if service:
            filename = f"My_School_Backup_{st.session_state.current_user.replace('@','_')}.json"
            results = service.files().list(q=f"name='{filename}' and trashed=false", fields="files(id)").execute()
            items = results.get('files', [])
            if items:
                request = service.files().get_media(fileId=items[0]['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                fh.seek(0)
                res = json.loads(fh.read().decode())
                st.session_state.school_info.update(res["school_info"])
                new_classes = {}
                for c_name, c_info in res["classes"].items():
                    new_classes[c_name] = {
                        "teacher": c_info["teacher"],
                        "subjects": c_info["subjects"],
                        "df": pd.read_json(io.StringIO(c_info["df_json"]), orient='split'),
                        "personal_info": c_info["personal_info"]
                    }
                st.session_state.all_classes_data = new_classes
                st.success("🎯 Data successfully loaded from your Google Drive!")
                time.sleep(1)
                st.rerun()
            else: st.error("No backup file found in your Google Drive.")

with main_tabs[2]:
    class_list = list(st.session_state.all_classes_data.keys())
    selected_class = st.selectbox(L["class_select"], class_list)
    current_class_data = st.session_state.all_classes_data[selected_class]
    
    # Subject Add
    st.write("---")
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1: new_sub = st.text_input(L["add_sub"])
    with col_s2: new_pass = st.number_input(L["pass_mark"], min_value=0, max_value=100, value=35)
    if st.button("➕ Add Subject") and new_sub:
        current_class_data["subjects"][new_sub] = new_pass
        current_class_data["df"][new_sub] = 0
        st.rerun()

    sub_tabs = st.tabs([L["tab_input"], L["tab_ranks"]])
    subjects = list(current_class_data["subjects"].keys())
    
    with sub_tabs[0]:
        df_edit = current_class_data["df"].copy()
        for col in ["Student ID", "Student Name"] + subjects:
            if col not in df_edit.columns: df_edit[col] = 0
        df_edit = df_edit[["Student ID", "Student Name"] + subjects]
        
        edited_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
        
        if st.button(L["save_btn"], type="primary", use_container_width=True):
            current_class_data["df"] = edited_df
            save_and_backup() # ලෝකල් සේව් එක සහ ගූගල් ඩ්‍රයිව් ඔටෝ බැකප් එක දෙකම එකවර සිදුවේ.
