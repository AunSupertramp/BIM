import streamlit as st
import pandas as pd
from PIL import Image, Image as pil_image
import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Frame, PageTemplate, BaseDocTemplate, Image as ReportlabImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
import time

# Register Thai fonts
pdfmetrics.registerFont(TTFont('Sarabun', r'./Font/THSarabunNew.ttf'))
pdfmetrics.registerFont(TTFont('Sarabun-Bold', r'./Font/THSarabunNew Bold.ttf'))

# Initialize session state attributes for notes and usage if they don't exist
if 'notes' not in st.session_state:
    st.session_state.notes = {}
if 'usage' not in st.session_state:
    st.session_state.usage = {}

# Set up the page
st.set_page_config(page_title='Clash Issues Note Report A4', page_icon=":vs:", layout='centered')
css_file = "styles/main.css"
with open(css_file) as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

st.title('Clash Issues Note Report')

# User input for project name
project_name = st.text_input("Please enter the project name", value="")

# File uploaders
csv_file = st.file_uploader("Upload CSV", type=['csv'])
uploaded_images = st.file_uploader("Upload Images", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

# Create a dictionary to map image names to their data
image_dict = {img.name: img.getvalue() for img in uploaded_images} if uploaded_images else {}

if csv_file:
    if 'df' not in st.session_state:
        st.session_state.df = pd.read_csv(csv_file, encoding='utf-8-sig')
    df = st.session_state.df

    df["Notes"].fillna("", inplace=True)
    df["Usage"].fillna("Tracking", inplace=True)
    df["Date Found"] = pd.to_datetime(df["Date Found"]).dt.strftime("%m/%d/%Y")
    # Drop the 'ImagePath' column
    if 'ImagePath' in df.columns:
        df.drop(columns=['ImagePath'], inplace=True)

    # Sidebar for filtering
    st.sidebar.header("Filter Options")
    filter_cols = ['Clash ID', 'View Name', 'Main Zone', 'Sub Zone', 'Level', 
                   'Issues Type', 'Issues Status', 'Discipline', 'Assign To', 'Usage']
    selected_values = {}
    for col in filter_cols:
        unique_values = df[col].unique().tolist()
        selected_values[col] = st.sidebar.selectbox(f'Select {col}', ['All'] + unique_values)
    
    # Apply filters to the session-stored DataFrame
    for col, value in selected_values.items():
        if value != 'All':
            df = df[df[col] == value]

    # Define the list of usage options
    usage_options = ['Tracking', 'High Priority', 'Not Used']

    # Display data with images and notes
    for idx, row in df.iterrows():
        img_name = row['Image']

        if img_name in image_dict:
            img = Image.open(BytesIO(image_dict[img_name]))

            # Two-column layout
            col1, col2 = st.columns([3, 3])
            with col1:
                st.write(f"<b>{row['View Name']}</b>", unsafe_allow_html=True)
                st.image(img, use_column_width=True)
            with col2:
                st.write(f"<b>Issue Type:</b> {row['Issues Type']}", unsafe_allow_html=True)
                st.write(f"<b>Issue Status:</b> {row['Issues Status']}", unsafe_allow_html=True)
                st.write(f"<b>Description:</b> {row['Description']}", unsafe_allow_html=True)

                note_key = f"note_{row['Clash ID']}_{idx}"
                initial_note = st.session_state.notes.get(note_key, row['Notes'])
                note = st.text_area(f"Add a note for {row['Clash ID']}", value=initial_note, key=note_key, height=150)
                df.at[idx, 'Notes'] = note
                st.session_state.notes[note_key] = note

                usage_key = f"usage_{row['Clash ID']}_{idx}"
                initial_usage_index = usage_options.index(row['Usage']) if row['Usage'] in usage_options else 0
                usage = st.selectbox('Select usage', usage_options, index=initial_usage_index, key=usage_key)

                df.at[idx, 'Usage'] = usage
                st.session_state.usage[usage_key] = usage
                
                if usage == 'Not Used':
                    df.at[idx, 'Issues Status'] = 'Resolved'

            st.markdown("---")
        else:
            st.write("Image not found")

    if st.button("Export CSV"):
        filename = datetime.datetime.now().strftime("%Y_%m_%d") + "_" + project_name + ".csv"
        csv_data = df.to_csv(encoding='utf-8-sig', index=False).encode('utf-8-sig')
        
        st.download_button(
            label="Download CSV",
            data=BytesIO(csv_data),
            file_name=filename,
            mime="text/csv"
        )

def generate_pdf(df, project_name):
    class MyDocTemplate(BaseDocTemplate):
        def __init__(self, filename, **kwargs):
            BaseDocTemplate.__init__(self, filename, **kwargs)
            page_width, page_height = A4
            frame_width = page_width
            frame_height = 0.8 * page_height
            frame_x = (page_width - frame_width) / 2  # shift frame to right by 1 cm
            frame_y = (page_height - frame_height) / 2
            frame = Frame(frame_x, frame_y, frame_width, frame_height, id='F1')
            template = PageTemplate('normal', [frame], onPage=self.add_page_decorations)
            self.addPageTemplates([template])


        def add_page_decorations(self, canvas, doc):
            with pil_image.open(logo_path) as img:
                width, height = img.size
            aspect = width / height
            new_height = 0.25 * inch
            new_width = new_height * aspect

            canvas.drawImage(logo_path, 0.2*inch, doc.height + 1.5*inch, width=new_width, height=new_height)

            canvas.setFont("Sarabun-Bold", 30)
            canvas.drawCentredString(doc.width/2 + 0.5*inch, doc.height + 1.2*inch + 0.25*inch, project_name)

            timestamp = time.strftime("%Y/%m/%d %H:%M:%S")
            canvas.setFont("Sarabun-Bold", 10)
            canvas.drawRightString(doc.width + inch, doc.height + inch + 0.75*inch, f"Generated on: {timestamp}")

    logo_path = r"./Media/1-Aurecon-logo-colour-RGB-Positive.png"
    output = BytesIO()
    pdf = MyDocTemplate(output, pagesize=A4)
    story = []

    # Header data
    header_data = ["No.", "Image", "Details"]
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    normal_style.fontName = 'Sarabun'
    normal_style.fontSize = 16

    bold_style = styles["Normal"]
    bold_style.fontName = 'Sarabun-Bold'
    bold_style.fontSize = 16

    # Table data
    data = [header_data]
    for idx, (index, row) in enumerate(df.iterrows(), 1):
        img_name = row['Image']
        if img_name in image_dict:
            image_path = ReportlabImage(BytesIO(image_dict[img_name]), width=2.4*inch, height=2.4*inch)
        else:
            image_path = "Image Not Found"

        
        details_list = [
            f"<b>Clash ID:</b> {row['Clash ID']}",
            f"<b>Date Found:</b> {row['Date Found']}",
            f"<b>Main Zone:</b> {row['Main Zone']}",
            f"<b>Description:</b> {row['Description']}",
            f"<b>Issue Type:</b> {row['Issues Type']}",
            f"<b>Issue Status:</b> {row['Issues Status']}",
        ]
        if row['Notes']:
            note_lines = row['Notes'].splitlines()
            details_list.append(f"<b>Note:</b> {note_lines[0]}")
            for line in note_lines[1:]:
                details_list.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{line}")

        details = "<br/>".join(details_list)
        details_paragraph = Paragraph(details, style=normal_style)
        data.append([str(idx), image_path, details_paragraph])

    # Define column widths
    page_width, page_height = A4 
    col_widths = [(0.1 * page_width), (0.3 * page_width), (0.4* page_width)]

    table_style = TableStyle([
    # Header settings
    ('BACKGROUND', (0, 0), (-1, 0), '#D5E1DD'),  # Background color for header row
    ('TEXTCOLOR', (0, 0), (-1, 0), '#2B2B2B'),  # Text color for header row
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center alignment for all cells
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Vertical alignment (top) for all cells
    ('FONTNAME', (0, 0), (-1, 0), 'Sarabun-Bold'),  # Bold font for header row
    ('FONTSIZE', (0, 0), (-1, 0), 18),  # Font size for header row
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Padding below the text for header row

    # Row settings
    ('BACKGROUND', (0, 1), (-1, -1), '#F5F5F5'),  # Background color for all rows except header
    ('GRID', (0, 0), (-1, -1), 1, '#2B2B2B'),  # Grid settings (black grid lines)

    # Font settings for "Details" and "No." columns
    ('FONTNAME', (0, 1), (-1, -1), 'Sarabun'),  # Font for all rows except header
    ('FONTSIZE', (1, 1), (1, -1), 16),  # Font size for "Details" column

    # Styling for "No." column
    ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Horizontal alignment for "No." column
    ('FONTNAME', (0, 0), (0, 0), 'Sarabun-Bold'),  # Bold font for "No." header
    ('FONTSIZE', (0, 0), (0, -1), 16)  # Font size for "No." column
])


    
    table = Table(data, colWidths=col_widths, repeatRows=1, style=table_style)
    story.append(table)
    pdf.build(story)
    return output.getvalue()

# Generate report button
if st.button("Generate Report"):
    pdf_data = generate_pdf(df, project_name)
    st.download_button(
        label="Download PDF Report",
        data=pdf_data,
        file_name=f"{datetime.datetime.now().strftime('%Y%m%d')}_ClashReport_{project_name}.pdf",
        mime="application/pdf"
    )
