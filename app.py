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
st.set_page_config(page_title="Android Teacher Portal", layout="wide", page_icon="🏫")

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- භාෂා පරිවර්තන ---
LANG_DICT = {
    "Sinhala": {
        "title": "🏫 ශ්‍රේණිගත පාසල් කළමනාකරණ Android පද්ධතිය",
        "home": "🏠 මුල් පිටුව", "settings": "⚙️ පද්ධති සැකසුම්", "workspace": "📊 පන්ති කාමර",
        "class_select": "🎯 වැඩ කිරීමට අවශ්‍ය පන්තිය තෝරන්න:", "add_class": "➕ අලුත් පන්තියක් සාදන්න",
        "sub_manage": "📚 විෂයයන් කළමනාකරණය", "add_sub": "අලුත් විෂයක් එකතු කරන්න:", "pass_mark": "සමත් ලකුණ:",
        "tab_input": "📝 ලකුණු ඇතුළත් කිරීම", "tab_ranks": "🏆 ශ්‍රේණිගත කිරීම් සහ PDF",
        "save_btn": "💾 වෙනස්කම් තහවුරු කර මගේ Google Drive වෙත සුරකින්න",
        "pdf_btn": "📥 නිල පන්ති වාර්තාව බාගත කරන්න (A4 PDF)"
    },
    "English": {
        "title": "🏫 Android Teacher Portal & Cloud Backup System",
        "home": "🏠 Home", "settings": "⚙️ Settings", "workspace": "📊 Class Workspaces",
        "class_select": "🎯 Select Class Workspace:", "add_class": "➕ Create New Class Workspace",
        "sub_manage": "📚 Subject Management", "add_sub": "Add New Subject:", "pass_mark": "Pass Mark:",
        "tab_input": "📝 Marks Input", "tab_ranks": "🏆 Class Rankings & PDF",
        "save_btn": "💾 Confirm Changes & Save to My Google Drive",
        "pdf_btn": "📥 Download Official Class Report (A4 PDF)"
    }
}

# --- දත්ත මතකය ආරම්භ කිරීම ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'gdrive_creds' not in st.session_state: st.session_state.gdrive_creds = {}
if 'all_classes_data' not in st.session_state:
    st.session_state.all_classes_data = {
        "10-A": {"teacher": "Class Teacher", "subjects": {"Mathematics": 35}, "df": pd.DataFrame([["ST001", "Kamal Perera", 85]], columns=["Student ID", "Student Name", "Mathematics"]), "personal_info": {}}
    }
if 'school_info' not in st.session_state:
    st.session_state.school_info = {"name": "පාසලේ නම ඇතුළත් කරන්න", "exam_type": "1st Term Exam"}

# ==========================================
# 🔐 1. ANDROID APP SIGN-UP & LOGIN ENGINE
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; color: #1A365D;'>🏫 Teacher Portal - Android App</h2>", unsafe_allow_html=True)
    login_tab, signup_tab = st.tabs(["🔒 Teacher Login", "📝 Register Account"])
    
    with signup_tab:
        r_email = st.text_input("Create Username (Email):", key="reg_email").strip()
        r_pass = st.text_input("Create Password:", type="password", key="reg_pass")
        st.caption("⚠️ සටහන: ගිණුම සෑදූ පසු ඔබගේ දත්ත ස්ථිරවම සුරැකීමට පෞද්ගලික Google Drive එක සම්බන්ධ කළ යුතුය.")
        if st.button("Register Account", use_container_width=True):
            if r_email and r_pass:
                # තාවකාලිකව මතකයේ තබා ගනී (පසුව Cloud එකට sync වේ)
                st.session_state.gdrive_creds[r_email] = {"password": r_pass, "token": None, "classes": {}, "school_info": {}}
                st.success("🎉 Account created! Please go to 'Teacher Login' tab now.")
            else: st.error("Please fill all fields.")
            
    with login_tab:
        l_email = st.text_input("Username (Email):", key="log_email").strip()
        l_pass = st.text_input("Password:", type="password", key="log_pass")
        
        if st.button("Sign In", type="primary", use_container_width=True):
            # ගිණුම පද්ධතියේ තිබේදැයි බලයි
            if l_email in st.session_state.gdrive_creds and st.session_state.gdrive_creds[l_email]["password"] == l_pass:
                st.session_state.logged_in = True
                st.session_state.current_user = l_email
                
                # කලින් Google Drive එක සම්බන්ධ කර තිබුණේ නම් Token එක ගනී
                user_record = st.session_state.gdrive_creds[l_email]
                if user_record.get("token"):
                    st.session_state[f"token_{l_email}"] = user_record["token"]
                st.rerun()
            else:
                st.error("❌ Invalid Username or Password! (වැරදිලා හරි App එක Refresh වුනා නම්, කරුණාකර නැවත වරක් Register වී ලොග් වන්න. ඉන්පසු වම්පස ඇති Connect බොත්තමෙන් Google Drive සම්බන්ධ කරන්න. එවිට ඔබගේ ගිණුම සදහටම සුරැකෙනු ඇත!)")
    st.stop()

# --- භාෂාව ---
selected_lang = st.sidebar.selectbox("🌐 Language:", ["Sinhala", "English"])
L = LANG_DICT[selected_lang]
user = st.session_state.current_user

# ==========================================
# ☁️ 2. GOOGLE DRIVE BACKUP & RECOVERY ENGINE
# ==========================================
st.sidebar.markdown(f"👤 **Teacher:** {user}")
st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ Cloud Auto-Sync")

token_key = f"token_{user}"
is_drive_connected = token_key in st.session_state

if not is_drive_connected:
    if 'oauth_flow' not in st.session_state:
        st.session_state.oauth_flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', scopes=SCOPES, redirect_uri='http://localhost'
        )
    auth_url, _ = st.session_state.oauth_flow.authorization_url(prompt='select_account')
    
    st.sidebar.warning("⚠️ ඔබගේ ගිණුම සහ දත්ත සදහටම ආරක්ෂා කිරීමට ප්‍රථමයෙන් Google Drive සම්බන්ධ කරන්න.")
    st.sidebar.markdown(f"[👉 Click Here to Connect Drive]({auth_url})", unsafe_allow_html=True)
    
    auth_code = st.sidebar.text_input("ලින්ක් එක/කේතය මෙතැනට පේස්ට් කරන්න:", key="android_auth_box")
    if st.sidebar.button("🔌 Connect Drive"):
        try:
            if "code=" in auth_code:
                auth_code = auth_code.split("code=")[1].split("&")[0]
            st.session_state.oauth_flow.fetch_token(code=auth_code)
            creds = st.session_state.oauth_flow.credentials
            
            # Token එක සේව් කරගනී
            token_json = json.loads(creds.to_json())
            st.session_state[token_key] = token_json
            st.session_state.gdrive_creds[user]["token"] = token_json
            
            # ස්වයංක්‍රීයව පරණ දත්ත තිබේ නම් Drive එකෙන් බාගත කරයි
            service = build('drive', 'v3', credentials=creds)
            filename = f"Teacher_App_Backup_{user.replace('@','_')}.json"
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
                st.session_state.school_info.update(res.get("school_info", {}))
                
                new_classes = {}
                for c_name, c_info in res.get("classes", {}).items():
                    new_classes[c_name] = {
                        "teacher": c_info["teacher"],
                        "subjects": c_info["subjects"],
                        "df": pd.read_json(io.StringIO(c_info["df_json"]), orient='split'),
                        "personal_info": c_info["personal_info"]
                    }
                st.session_state.all_classes_data = new_classes
                st.sidebar.success("📥 ඩ්‍රයිව් එකේ තිබූ පැරණි දත්ත සියල්ල සාර්ථකව ලෝඩ් වුණා!")
            else:
                st.sidebar.success("🚀 අලුත්ම Cloud Backup එකක් සක්‍රීය වුණා!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.sidebar.error("සම්බන්ධතාව අසාර්ථකයි. නැවත උත්සාහ කරන්න.")
else:
    st.sidebar.success("☁️ Google Cloud Sync: Active")

# --- Cloud Save Function ---
def sync_data_to_user_drive():
    if token_key not in st.session_state:
        st.sidebar.error("කරුණාකර ප්‍රථමයෙන් Google Drive සම්බන්ධ කරන්න!")
        return
        
    try:
        creds = Credentials.from_authorized_user_info(st.session_state[token_key], SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        filename = f"Teacher_App_Backup_{user.replace('@','_')}.json"
        
        backup_payload = {
            "password": st.session_state.gdrive_creds[user]["password"],
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
        
        results = service.files().list(q=f"name='{filename}' and trashed=false", fields="files(id)").execute()
        items = results.get('files', [])
        
        if items:
            service.files().update(fileId=items[0]['id'], media_body=media).execute()
            st.toast("🔄 Cloud Backup Updated!", icon="☁️")
        else:
            file_metadata = {'name': filename, 'mimeType': 'application/json'}
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            st.toast("🚀 Initial Cloud Backup Saved!", icon="☁️")
    except Exception as e:
        st.error(f"Cloud Save Error: {str(e)}")

# ==========================================
# 📊 3. MAIN WORKSPACE UI
# ==========================================
st.title(L["title"])

main_tabs = st.tabs([L["home"], L["settings"], L["workspace"]])

with main_tabs[0]:
    st.subheader(L["home"])
    st.markdown(f"### ආයුබෝවන්, {user} 🧑‍🏫")
    st.info("💡 App එක පළමු වරට පාවිච්චි කිරීමේදී වම්පස ඇති 'Connect Drive' ලින්ක් එක ක්ලික් කර ඔබගේ Google Drive එක සම්බන්ධ කරන්න. ඉන්පසු ලකුණු ඇතුළත් කර Save කළ විට, App එක කීපාරක් වැසුණත් ඔබගේ Login එක සහ දත්ත කිසිදා මැකී යන්නේ නැත!")

with main_tabs[1]:
    st.subheader(L["settings"])
    st.session_state.school_info['name'] = st.text_input("School Name:", st.session_state.school_info['name'])
    st.session_state.school_info['exam_type'] = st.text_input("Exam Type:", st.session_state.school_info['exam_type'])
    if st.button("💾 Save Settings"):
        sync_data_to_user_drive()

with main_tabs[2]:
    class_list = list(st.session_state.all_classes_data.keys())
    selected_class = st.selectbox(L["class_select"], class_list)
    current_class_data = st.session_state.all_classes_data[selected_class]
    
    # Subject Adding
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
            sync_data_to_user_drive() # ලෝකල් දත්ත සේව් කර සැනින් ගූගල් ඩ්‍රයිව් එකට යවයි
            st.success("Saved & Backed up to Google Drive!")
