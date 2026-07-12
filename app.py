import streamlit as st
import pandas as pd
import json
import os
import time
import io
import warnings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Google Drive Libraries
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# අනවශ්‍ය Parameter Warnings සම්පූර්ණයෙන්ම මඟහරියි
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Premium Multi-Class Management Portal", layout="wide", page_icon="🏫")

# Google Drive Scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- භාෂා පරිවර්තන දත්ත පද්ධතිය ---
LANG_DICT = {
    "Sinhala": {
        "title": "🏫 උසස් පාසල් ප්‍රතිඵල සහ ස්වයංක්‍රීය Cloud සංරක්ෂණ පද්ධතිය",
        "home": "🏠 මුල් පිටුව", "settings": "⚙️ පාසල් සැකසුම්", "workspace": "📊 පන්ති කාමර", "profiles": "👤 ශිෂ්‍ය පුද්ගලික විස්තර",
        "select_lang": "🌐 භාෂාව තෝරන්න:", "sch_name": "පාසලේ නම:", "exam_type": "විභාග වර්ගය:", "year": "වර්ෂය:",
        "class_select": "🎯 වැඩ කිරීමට අවශ්‍ය පන්තිය තෝරන්න:", "add_class": "➕ අලුත් පන්තියක් සාදන්න", "teacher": "🧑‍🏫 පන්තිභාර ගුරුතුමා/ගුරුතුමිය:",
        "sub_manage": "📚 විෂයයන් කළමනාකරණය", "add_sub": "අලුත් විෂයක් එකතු කරන්න:", "pass_mark": "සමත් ලකුණ:",
        "tab_input": "📝 ලකුණු ඇතුළත් කිරීම", "tab_grades": "📊 ශිෂ්‍ය සාමාර්ථ", "tab_ranks": "🏆 ශ්‍රේණිගත කිරීම් සහ PDF",
        "tab_charts": "📊 විෂය විශ්ලේෂණ ප්‍රස්ථාර",
        "save_btn": "💾 සියලුම ලකුණු සුරකින්න", "photo_toggle": "📸 PDF වාර්තාවට ළමුන්ගේ පින්තූර ඇතුළත් කරන්න",
        "pdf_btn": "📥 නිල පන්ති වාර්තාව බාගත කරන්න (A4 PDF)", "search": "🔍 ශිෂ්‍ය නම හෝ ID මඟින් සොයන්න:", "save_profile": "💾 පුද්ගලික විස්තර සුරකින්න",
        "class_ops": "🛠️ පන්ති පරිපාලනය (Advanced Class Operations)",
        "chart_title": "📊 එක් එක් විෂය සඳහා සාමාර්ථ විශ්ලේෂණය (Grade Distribution per Subject)",
        "select_sub_chart": "📈 ප්‍රස්ථාරය බැලීමට විෂය තෝරන්න:"
    },
    "Tamil": {
        "title": "🏫 மேம்பட்ட பள்ளி செயல்திறன் மற்றும் தானியங்கி மேகக்கணி காப்பு முறைமை",
        "home": "🏠 முகப்பு", "settings": "⚙️ பள்ளி அமைப்புகள்", "workspace": "📊 வகுப்பறைகள்", "profiles": "👤 மாணவர் சுயவிவரம்",
        "select_lang": "🌐 மொழியைத் தேர்வுசெய்க:", "sch_name": "பள்ளியின் பெயர்:", "exam_type": "தேர்வு வகை:", "year": "ஆண்டு:",
        "class_select": "🎯 வேலை செய்ய வேண்டிய வகுப்பைத் தேர்ந்தெடுக்கவும்:", "add_class": "➕ புதிய வகுப்பை உருவாக்குங்கள்", "teacher": "🧑‍🏫 வகுப்பு ஆசிரியர் பெயர்:",
        "sub_manage": "📚 பாடங்கள் மேலாண்மை", "add_sub": "புதிய பாடத்தைச் சேர்க்கவும்:", "pass_mark": "தேர்ச்சி புள்ளி:",
        "tab_input": "📝 மதிப்பெண்கள் உள்ளீடு", "tab_grades": "📊 மாணவர் தரங்கள்", "tab_ranks": "🏆 தரவரிசை மற்றும் PDF",
        "tab_charts": "📊 பாட வாரியான வரைபடங்கள்",
        "save_btn": "💾 மதிப்பெண்களைச் சேமிக்கவும்", "photo_toggle": "📸 PDF அறிக்கையில் மாணவர் புகைப்படங்களைச் சேர்க்கவும்",
        "pdf_btn": "📥 உத்தியோகபூர்வ வகுப்பு அறிக்கையைப் பதிவிறக்கவும் (A4 PDF)", "search": "🔍 மாணவர் பெயர் அல்லது ID மூலம் தேடவும்:", "save_profile": "💾 சுயவிவரத்தைச் சேமிக்கவும்",
        "class_ops": "🛠️ வகுப்பு மேலாண்மை (Advanced Class Operations)",
        "chart_title": "📊 பாட வாரியான தரப் பகிர்வு (Grade Distribution per Subject)",
        "select_sub_chart": "📈 வரைபடத்தைப் பார்க்க பாடத்தைத் தேர்ந்தெடுக்கவும்:"
    },
    "English": {
        "title": "🏫 Advanced School Performance & Auto Cloud Backup System",
        "home": "🏠 Home & Overview", "settings": "⚙️ School Settings", "workspace": "📊 Class Workspaces", "profiles": "👤 Student Profiles",
        "select_lang": "🌐 Select Language:", "sch_name": "School Name:", "exam_type": "Exam Type:", "year": "Academic Year:",
        "class_select": "🎯 Select Class Workspace:", "add_class": "➕ Create New Class Workspace", "teacher": "🧑‍🏫 Class Teacher Name:",
        "sub_manage": "📚 Subject Management", "add_sub": "Add New Subject:", "pass_mark": "Pass Mark:",
        "tab_input": "📝 Marks & Photos Input", "tab_grades": "📊 Student Grades", "tab_ranks": "🏆 Class Rankings & PDF",
        "tab_charts": "📊 Subject Analysis Charts",
        "save_btn": "💾 Save All Marks Changes", "photo_toggle": "📸 Include Student Photos in PDF Report",
        "pdf_btn": "📥 Download Official Class Report (A4 PDF)", "search": "🔍 Search Student by Name or ID:", "save_profile": "💾 Save Personal Profile",
        "class_ops": "🛠️ Advanced Class Actions (Edit / Delete)",
        "chart_title": "📊 Grade Distribution Analysis per Subject",
        "select_sub_chart": "📈 Select Subject to View Chart:"
    }
}

if 'user_db' not in st.session_state: st.session_state.user_db = {"teacher@school.com": "password123"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = None

# --- GOOGLE DRIVE BACKUP ENGINE ---
def get_drive_service():
    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('drive', 'v3', credentials=creds)

def trigger_auto_backup():
    if not st.session_state.logged_in: return
    
    filename = f"Backup_{st.session_state.current_user.replace('@','_')}.json"
    backup_payload = {
        "school_info": {k: v for k, v in st.session_state.school_info.items() if k != 'photo'},
        "classes": {}
    }
    for c_name, c_info in st.session_state.all_classes_data.items():
        backup_payload["classes"][c_name] = {
            "teacher": c_info["teacher"],
            "subjects": c_info["subjects"],
            "df_json": c_info["df"].to_json(orient='split'),
            "personal_info": c_info["personal_info"]
        }
        
    try:
        service = get_drive_service()
        json_data = json.dumps(backup_payload)
        query = f"name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        media = MediaIoBaseUpload(io.BytesIO(json_data.encode()), mimeType='application/json', resumable=True)
        
        if items:
            file_id = items[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            st.toast("🔄 Auto-Backup: Cloud updated successfully!", icon="☁️")
        else:
            file_metadata = {'name': filename, 'mimeType': 'application/json'}
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            st.toast("☁️ Auto-Backup: Initial cloud file created!", icon="🚀")
    except Exception as e:
        pass 

def restore_from_drive():
    filename = f"Backup_{st.session_state.current_user.replace('@','_')}.json"
    try:
        service = get_drive_service()
        results = service.files().list(q=f"name='{filename}'", fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items: return False
        
        file_id = items[0]['id']
        request = service.files().get_media(fileId=file_id)
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
        return True
    except:
        return False

def calculate_grade(score, pass_mark):
    try: score = float(score)
    except: score = 0
    if score == 0: return "AB"
    elif score >= 75: return "A"
    elif score >= 65: return "B"
    elif score >= 55: return "C"
    elif score >= pass_mark: return "S"
    else: return "F"

# ==========================================
# 🔐 LOGIN / SIGN-UP SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #1A365D;'>🏫 School Report Portal</h1>", unsafe_allow_html=True)
    login_tab, signup_tab = st.tabs(["🔒 Teacher Login", "📝 Register New Account"])
    
    with login_tab:
        l_email = st.text_input("Email Address:", key="le")
        l_pass = st.text_input("Password:", type="password", key="lp")
        if st.button("Sign In", type="primary"):
            if l_email in st.session_state.user_db and st.session_state.user_db[l_email] == l_pass:
                st.session_state.logged_in = True
                st.session_state.current_user = l_email
                st.rerun()
            else: st.error("Invalid credentials")
    with signup_tab:
        r_email = st.text_input("Email:", key="re")
        r_pass = st.text_input("Password:", type="password", key="rp")
        if st.button("Register"):
            st.session_state.user_db[r_email] = r_pass
            st.success("Registered successfully!")
    st.stop()

# --- දත්ත ආරම්භ කිරීම ---
if 'all_classes_data' not in st.session_state:
    st.session_state.all_classes_data = {
        "10-A": {"teacher": "Mr. Asela Perera", "subjects": {"Mathematics": 35, "Science": 35}, "df": pd.DataFrame([["ST001", "Kamal Perera", 85, 74], ["ST002", "Nimal Silva", 45, 0]], columns=["Student ID", "Student Name", "Mathematics", "Science"]), "personal_info": {}},
    }
if 'student_photos' not in st.session_state: st.session_state.student_photos = {}
if 'school_info' not in st.session_state: st.session_state.school_info = {"name": "බ/මහි / හදන්නාව මහා විද්‍යාලය", "exam_type": "1st Term Exam", "year": "2026", "photo": None}

selected_lang = st.sidebar.selectbox("🌐 Language:", ["English", "Sinhala", "Tamil"])
L = LANG_DICT[selected_lang]

main_tabs = st.tabs([L["home"], L["settings"], L["workspace"], L["profiles"]])

# TAB 1: HOME
with main_tabs[0]:
    st.markdown(f"<h1 style='text-align: center; color: #1A365D;'>🏫 {st.session_state.school_info['name']}</h1>", unsafe_allow_html=True)
    st.write("---")
    summary_data = [[c_name, c_info["teacher"], len(c_info["df"]), len(c_info["subjects"])] for c_name, c_info in st.session_state.all_classes_data.items()]
    if summary_data: st.table(pd.DataFrame(summary_data, columns=["Class", "Teacher", "Total Students", "Total Subjects"]))

# TAB 2: SETTINGS
with main_tabs[1]:
    st.subheader(L["settings"])
    st.session_state.school_info['name'] = st.text_input(L["sch_name"], st.session_state.school_info['name'])
    
    st.write("---")
    st.markdown("### ☁️ Google Drive Cloud Data Sync")
    if st.button("📥 Load Existing Backup From Cloud", use_container_width=True):
        if restore_from_drive(): st.success("Data successfully loaded!")
        else: st.error("No backup found or connection failed.")

# TAB 3: WORKSPACES (CLASS ACTIONS & ANALYSIS CHARTS)
with main_tabs[2]:
    class_list = list(st.session_state.all_classes_data.keys())
    
    st.markdown(f"#### {L['class_select']}")
    selected_class = st.selectbox("Choose Workspace:", class_list, label_visibility="collapsed")
    current_class_data = st.session_state.all_classes_data[selected_class]
    
    # 🛠️ ADVANCED CLASS ACTIONS
    with st.expander(f"⚙️ {L['class_ops']}", expanded=False):
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.markdown("##### 📝 Rename / Edit Current Class")
            rename_class_name = st.text_input("🔄 Edit Class Name:", value=selected_class)
            edit_teacher_name = st.text_input("🧑‍🏫 Edit Teacher Name:", value=current_class_data["teacher"])
            
            if st.button("💾 Save Class Info Changes", type="secondary"):
                if rename_class_name and rename_class_name != selected_class:
                    st.session_state.all_classes_data[rename_class_name] = st.session_state.all_classes_data.pop(selected_class)
                    st.session_state.all_classes_data[rename_class_name]["teacher"] = edit_teacher_name
                    st.success(f"Class updated successfully!")
                else:
                    st.session_state.all_classes_data[selected_class]["teacher"] = edit_teacher_name
                    st.success("Teacher name updated successfully!")
                trigger_auto_backup() 
                time.sleep(0.5)
                st.rerun()

        with c_col2:
            st.markdown("##### 🗑️ Delete Class")
            if st.button(f"🚨 Delete {selected_class} Permanently", type="primary", use_container_width=True):
                if len(st.session_state.all_classes_data) > 1:
                    st.session_state.all_classes_data.pop(selected_class)
                    trigger_auto_backup()
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("⚠️ Error: System must contain at least one class!")

        st.write("---")
        st.markdown(f"##### {L['add_class']}")
        new_c_name = st.text_input("📂 New Class Name (e.g., 10-C):")
        new_c_teacher = st.text_input("🧑‍🏫 New Class Teacher Name:")
        if st.button("🚀 Create Class Workspace"):
            if new_c_name and new_c_name not in st.session_state.all_classes_data:
                st.session_state.all_classes_data[new_c_name] = {"teacher": new_c_teacher if new_c_teacher else "Teacher", "subjects": {"Mathematics": 35}, "df": pd.DataFrame(columns=["Student ID", "Student Name", "Mathematics"]), "personal_info": {}}
                trigger_auto_backup()
                time.sleep(0.5)
                st.rerun()
                
    st.write("---")
    st.markdown(f"### Current Active Workspace: **{selected_class}** (Teacher: {current_class_data['teacher']})")
    
    # Subject Add
    st.subheader(L["sub_manage"])
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1: new_sub = st.text_input(L["add_sub"])
    with col_s2: new_pass = st.number_input(L["pass_mark"], min_value=0, max_value=100, value=35, key="sub_pm_chart")
    if st.button("➕ Add Subject") and new_sub:
        current_class_data["subjects"][new_sub] = new_pass
        current_class_data["df"][new_sub] = 0
        trigger_auto_backup() 
        st.rerun()

    # SUB TABS
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([L["tab_input"], L["tab_grades"], L["tab_ranks"], L["tab_charts"]])
    subjects = list(current_class_data["subjects"].keys())
    
    with sub_tab1:
        df_edit = current_class_data["df"].copy()
        for col in ["Student ID", "Student Name"] + subjects:
            if col not in df_edit.columns: df_edit[col] = 0
        df_edit = df_edit[["Student ID", "Student Name"] + subjects]
        
        edited_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True, key=f"editor_c_{selected_class}")
        if st.button(L["save_btn"], type="primary"):
            current_class_data["df"] = edited_df
            trigger_auto_backup() 
            st.success("Saved & Cloud Synced Automatically!")

    # Processing Ranks
    df_processed = current_class_data["df"].copy()
    if len(subjects) > 0 and not df_processed.empty:
        for sub in subjects:
            df_processed[sub] = pd.to_numeric(df_processed[sub], errors='coerce').fillna(0)
            df_processed[f"{sub} (Grade)"] = df_processed[sub].apply(lambda x: calculate_grade(x, current_class_data["subjects"].get(sub, 35)))
        df_processed['Total'] = df_processed[subjects].sum(axis=1)
        df_processed['Average'] = df_processed[subjects].mean(axis=1).round(2)
        df_processed['Rank'] = df_processed['Total'].rank(ascending=False, method='min').astype(int)
        df_processed = df_processed.sort_values(by="Rank")

    with sub_tab2:
        if not df_processed.empty: st.dataframe(df_processed[["Student ID", "Student Name"] + [f"{sub} (Grade)" for sub in subjects]], use_container_width=True)
        
    with sub_tab3:
        if not df_processed.empty:
            st.dataframe(df_processed[["Rank", "Student ID", "Student Name"] + subjects + ["Total", "Average"]], use_container_width=True)
            include_photos = st.toggle(L["photo_toggle"], value=True, key="p_t_c")
            
            if st.button(L["pdf_btn"]):
                buffer = io.BytesIO()
                page_layout = landscape(A4) if len(subjects) > 5 else A4
                available_width = 698 if len(subjects) > 5 else 451
                
                doc = SimpleDocTemplate(buffer, pagesize=page_layout, leftMargin=72, rightMargin=72, topMargin=54, bottomMargin=54)
                elements = []
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=15, alignment=1, textColor=colors.white)
                cell_style = ParagraphStyle('C', parent=styles['Normal'], fontSize=9, alignment=1)
                
                header_text = f"<b>{st.session_state.school_info['name']}</b><br/>{st.session_state.school_info['exam_type']}"
                header_table = Table([[Paragraph(header_text, title_style)]], colWidths=[available_width])
                header_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1A365D")), ('PADDING', (0,0), (-1,-1), 10)]))
                elements.append(header_table)
                elements.append(Spacer(1, 15))
                
                pdf_cols = ["Rank"]
                if include_photos: pdf_cols.append("Photo")
                pdf_cols += ["Student Name"] + [s for s in subjects] + ["Total", "Average"]
                
                table_data = [[Paragraph(f"<b>{c}</b>", ParagraphStyle('H', parent=styles['Normal'], fontSize=9, textColor=colors.white, alignment=1)) for c in pdf_cols]]
                
                for _, row in df_processed.iterrows():
                    s_id = row['Student ID']
                    row_cells = [Paragraph(str(row['Rank']), cell_style)]
                    if include_photos:
                        img_flowable = RLImage(io.BytesIO(st.session_state.student_photos[s_id]), width=22, height=22) if s_id in st.session_state.student_photos else Paragraph("-", cell_style)
                        row_cells.append(img_flowable)
                    row_cells.append(Paragraph(str(row['Student Name']), styles['Normal']))
                    for sub in subjects:
                        row_cells.append(Paragraph(f"{int(row[sub])}<br/><font color='gray'>({row[f'{sub} (Grade)']})</font>", cell_style))
                    row_cells.append(Paragraph(str(int(row['Total'])), cell_style))
                    row_cells.append(Paragraph(str(row['Average'])+"%", cell_style))
                    table_data.append(row_cells)
                    
                t = Table(table_data, repeatRows=1)
                t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]), ('PADDING', (0,0), (-1,-1), 6)]))
                elements.append(t)
                
                elements.append(Spacer(1, 40))
                sig_w = available_width / 2
                sig_table = Table([[Paragraph("..........................................<br/>Class Teacher Signature", cell_style), Paragraph("..........................................<br/>Principal Signature", cell_style)]], colWidths=[sig_w, sig_w])
                elements.append(sig_table)
                
                doc.build(elements)
                st.download_button("💾 Save PDF Report", data=buffer.getvalue(), file_name="Official_Report.pdf")

    # ==========================================
    # 🔥 SUBJECT ANALYSIS CHARTS
    # ==========================================
    with sub_tab4:
        st.markdown(f"### {L['chart_title']}")
        if len(subjects) == 0 or df_processed.empty:
            st.warning("ප්‍රස්ථාර බැලීමට ප්‍රමාණවත් විෂයයන් හෝ සිසුන්ගේ ලකුණු දත්ත පද්ධතියේ නැත.")
        else:
            selected_chart_sub = st.selectbox(L["select_sub_chart"], subjects)
            grade_col = f"{selected_chart_sub} (Grade)"
            possible_grades = ["A", "B", "C", "S", "F", "AB"]
            grade_counts = df_processed[grade_col].value_counts()
            
            chart_data = pd.DataFrame({
                "Grade": possible_grades,
                "Count": [grade_counts.get(g, 0) for g in possible_grades]
            }).set_index("Grade")
            
            st.bar_chart(chart_data, color="#2B6CB0", use_container_width=True)
            st.markdown("#### 📝 Summary Table")
            st.dataframe(chart_data.T, use_container_width=True)

# TAB 4: PROFILES
with main_tabs[3]:
    st.subheader(L["profiles"])
    prof_class = st.selectbox(L["class_select"], list(st.session_state.all_classes_data.keys()), key="pc_chart_sel")
    class_data = st.session_state.all_classes_data[prof_class]
    
    if not class_data["df"].empty:
        search_query = st.text_input(L["search"], "")
        filtered = [f"[{row['Student ID']}] {row['Student Name']}" for idx, row in class_data["df"].iterrows() if search_query.lower() in str(row['Student Name']).lower()]
        
        if filtered:
            selected_s = st.selectbox("Select Student:", filtered)
            s_id = selected_s.split("]")[0].replace("[", "").strip()
            
            if s_id not in class_data["personal_info"]: class_data["personal_info"][s_id] = {"DOB": "", "Gender": "Male", "Address": "", "Guardian": "", "Phone": ""}
            prof = class_data["personal_info"][s_id]
            
            p_dob = st.text_input("📅 DOB:", prof["DOB"])
            p_gender = st.selectbox("Gender:", ["Male", "Female"], index=0 if prof["Gender"]=="Male" else 1)
            p_address = st.text_area("Address:", prof["Address"])
            p_guardian = st.text_input("Guardian Name:", prof["Guardian"])
            p_phone = st.text_input("Phone Number:", prof["Phone"])
            
            if st.button(L["save_profile"]):
                class_data["personal_info"][s_id] = {"DOB": p_dob, "Gender": p_gender, "Address": p_address, "Guardian": p_guardian, "Phone": p_phone}
                trigger_auto_backup() 
                st.success("Profile Saved & Cloud Synced Automatically!")
