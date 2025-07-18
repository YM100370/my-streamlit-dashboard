import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io

# --- ייבוא ספריות לייצוא PDF ---
# ודא שהתקנת אותן: pip install reportlab kaleido
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT # ליישור טקסט

# --- הגדרות עמוד ---
st.set_page_config(
    page_title="Bakery Sales Dashboard 🥐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Bakery Sales Dashboard")

# --- CSS מותאם אישית ---
st.markdown("""
<style>
/* יישור כותרות הטבלה למרכז */
.stTable thead th {
    text-align: center !important;
}

/* יישור תוכן תאי הטבלה (מספרים) למרכז */
.stTable tbody td {
    text-align: center !important;
}

/* הקטנת רוחב הטבלה ב-30% ויישור למרכז */
div[data-testid="stVerticalBlock"] > div > div > div:has(div.stTable) {
    width: 70% !important;
    margin-left: auto;
    margin-right: auto;
}

/* יישור כותרות משנה (st.subheader) למרכז */
h3 {
    text-align: center;
    width: 100%;
}

/* ------------------------------------------- */
/* עיצוב חדש עבור מדדי המפתח (KPI) */
/* ------------------------------------------- */

/* מעצב ישירות את הקונטיינר הראשי של כל st.metric */
div[data-testid="stMetric"] {
    border: 1px solid #ddd; /* גבול עדין */
    border-radius: 8px;      /* פינות מעוגלות */
    padding: 15px;           /* ריפוד פנימי */
    box-shadow: 2px 2px 8px rgba(0,0,0,0.1); /* צל עדין */
    background-color: #f9f9f9; /* צבע רקע מעט שונה */
    margin-bottom: 10px; /* רווח מתחת לכל קובייה */
    
    /* מאפייני Flexbox כדי למרכז את התוכן בתוך ה-st.metric */
    display: flex;
    flex-direction: column; /* תוכן המדד (תווית וערך) מסודרים אנכית */
    justify-content: center; /* יישור אנכי למרכז */
    align-items: center;    /* יישור אופקי למרכז */
    min-height: 100px;       /* גובה מינימלי לקובייה כדי שהיישור ייראה טוב */
    width: 100%;             /* ודא שה-metric תופס את כל הרוחב בעמודה שלו */
}

/* יישור הערך של המדד למרכז */
div[data-testid="stMetricValue"] {
    text-align: center !important;
    font-size: 1.8em !important;
    font-weight: bold !important;
    line-height: 1.2 !important; /* רווח שורה לקריאות טובה יותר */
}

/* יישור התווית של המדד למרכז */
div[data-testid="stMetricLabel"] {
    text-align: center !important;
    font-size: 0.9em !important;
    color: #555 !important;
    line-height: 1.2 !important; /* רווח שורה */
}

/* יישור של הטולטיפ (אייקון המידע הקטן) למרכז בתוך התווית */
.stMetric span[data-testid="stMetricLabelWithHelpText"] {
    display: flex !important; /* הופך את הספאן לפלקס קונטיינר */
    flex-direction: row !important; /* שומר על הטקסט והאייקון באותה שורה */
    justify-content: center !important; /* ממקם אותם במרכז */
    align-items: center !important; /* מיישר אנכית */
    width: 100% !important; /* ודא שתופס את כל הרוחב */
}
/* ודא שהאייקון עצמו לא נפרד מהטקסט */
.stMetric .stTooltipIcon {
    margin-right: 5px !important; /* רווח קטן בין הטקסט לאייקון */
}

</style>
""", unsafe_allow_html=True)


# --- טעינת נתונים --- 
csv_path = "bakery_sales_revised.csv"
if not os.path.exists(csv_path):
    st.error(f"קובץ הנתונים לא נמצא בנתיב: `{csv_path}`. אנא ודא את הנתיב והרשאות.")
    st.stop()

try:
    df = pd.read_csv(csv_path)
except Exception as e:
    st.error(f"שגיאה בטעינת הקובץ: {e}. ודא שהקובץ תקין ונגיש.")
    st.stop()

# --- בדיקת עמודות קריטיות ---
required_columns = ['date_time', 'Transaction', 'Item']
for col_name in required_columns:
    if col_name not in df.columns:
        st.error(f"חסרה עמודת '{col_name}' בקובץ הנתונים. אנא ודא את מבנה הקובץ.")
        st.stop()

# --- עיבוד נתונים ראשוני (לפני פילטור) ---
df['date_time'] = pd.to_datetime(df['date_time'], errors='coerce')
df = df.dropna(subset=['date_time']) # הסרת שורות עם תאריכים לא חוקיים

# קביעת תאריכי ברירת מחדל לפילטר: התאריך המוקדם והמאוחר ביותר בנתונים
min_overall_date = df['date_time'].min().date()
max_overall_date = df['date_time'].max().date()

# יצירת עמודת שנה-חודש (YYYY-MM) לגרף המגמה (לפני פילטור כי נשתמש בזה לסך המכירות הכללי)
df['YearMonth'] = df['date_time'].dt.to_period('M').astype(str)

# חישוב סך המכירות לכל מוצר (כדי להשתמש בזה בטבלת הקפה) - נשאר גלובלי לכלל הנתונים
total_item_sales = df['Item'].value_counts().reset_index()
total_item_sales.columns = ['Item', 'TotalSales']

# קבלת רשימת המוצרים הייחודיים עבור פילטר המוצר
all_items_options = ['כל המוצרים'] + sorted(df['Item'].unique().tolist())

# --- אתחול St.session_state לניהול פילטרים ---
if 'start_date' not in st.session_state:
    st.session_state.start_date = min_overall_date
if 'end_date' not in st.session_state:
    st.session_state.end_date = max_overall_date
if 'selected_item' not in st.session_state: # זה המשתנה שנשתמש בו לסינון
    st.session_state.selected_item = 'כל המוצרים'


# --- פונקציות קולבק לעדכון פילטרים ---
def update_start_date():
    """מעדכן את st.session_state.start_date כאשר ה-date_input מתאריך משתנה."""
    st.session_state.start_date = st.session_state.start_date_widget_key

def update_end_date():
    """מעדכן את st.session_state.end_date כאשר ה-date_input עד תאריך משתנה."""
    st.session_state.end_date = st.session_state.end_date_widget_key

def update_selected_item_filter():
    """מעדכן את st.session_state.selected_item כאשר ה-selectbox משתנה."""
    st.session_state.selected_item = st.session_state.product_selectbox_widget_key


def reset_filters():
    """מאפס את כל הפילטרים לערכי ברירת המחדל."""
    st.session_state.start_date = min_overall_date
    st.session_state.end_date = max_overall_date
    st.session_state.selected_item = 'כל המוצרים'
    
    # כדי לוודא שגם הווידג'טים מתאפסים חזותית, נעדכן את ה-keys שלהם
    st.session_state.start_date_widget_key = min_overall_date
    st.session_state.end_date_widget_key = max_overall_date
    st.session_state.product_selectbox_widget_key = 'כל המוצרים'
    
    # אין צורך ב-st.rerun() כאן. שינוי st.session_state כבר גורם לריצה מחדש.
    # האזהרה "no-op" תיעלם כי אנחנו לא קוראים ל-rerun בתוך הקולבק.


# --- סרגל צד לפילטרים ---
with st.sidebar:
    st.header("🔍 פילטרים")
    
    st.write("בחר טווח תאריכים לסינון הנתונים:")
    st.date_input(
        "מתאריך",
        min_value=min_overall_date,
        max_value=max_overall_date,
        value=st.session_state.start_date,
        key="start_date_widget_key", # Key for the widget
        on_change=update_start_date # Callback for this date input
    )
    st.date_input(
        "עד תאריך",
        min_value=min_overall_date,
        max_value=max_overall_date,
        value=st.session_state.end_date,
        key="end_date_widget_key", # Key for the widget
        on_change=update_end_date # Callback for this date input
    )

    if st.session_state.start_date > st.session_state.end_date:
        st.error("שגיאה: תאריך ההתחלה חייב להיות קטן או שווה לתאריך הסיום.")
        st.stop()
    
    st.markdown("---")

    st.write("בחר מוצר לסינון הנתונים:")
    st.selectbox(
        "בחר מוצר",
        options=all_items_options,
        index=all_items_options.index(st.session_state.selected_item),
        key="product_selectbox_widget_key", # זה ה-key של הווידג'ט עצמו
        on_change=update_selected_item_filter # הקולבק שירוץ בעת שינוי
    )
    
    st.markdown("---")
    
    st.button("איפוס פילטרים", on_click=reset_filters)

    st.markdown("---")
    st.info("💡 טיפ: השתמש בפילטרים לניתוח מעמיק יותר של נתוני המאפייה שלך.")

# --- סינון הנתונים לפי טווח התאריכים ומוצר נבחר ---
# הסינון מתבצע על בסיס הערכים המעודכנים ב-st.session_state
df_filtered = df[(df['date_time'].dt.date >= st.session_state.start_date) & 
                 (df['date_time'].dt.date <= st.session_state.end_date)].copy()

if st.session_state.selected_item != "כל המוצרים":
    df_filtered = df_filtered[df_filtered['Item'] == st.session_state.selected_item]

# בדיקה אם יש נתונים לאחר הסינון
if df_filtered.empty:
    st.warning("אין נתונים בטווח התאריכים או עבור המוצר שנבחרו. אנא בחר פילטרים אחרים.")
    st.stop()


# --- חישוב KPI's על הנתונים המסוננים ---
total_items_sold = len(df_filtered)
unique_transactions = df_filtered['Transaction'].nunique()

if unique_transactions > 0:
    avg_items_per_transaction = total_items_sold / unique_transactions
else:
    avg_items_per_transaction = 0

# --- KPI's (מדדי ביצועים מרכזיים) ---
st.subheader("📈 מדדי מפתח")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("סה\"כ עסקאות", unique_transactions, help="מספר העסקאות הייחודיות שבוצעו במאפייה בטווח התאריכים והמוצר הנבחרים.")

with col2:
    st.metric("סה\"כ פריטים שנמכרו", total_items_sold, help="הכמות הכוללת של פריטים שנמכרו בכל העסקאות בטווח התאריכים והמוצר הנבחרים.")

with col3:
    st.metric("מספר פריטים ייחודיים", df_filtered['Item'].nunique(), help="מספר סוגי הפריטים השונים (מוצרים) הנמכרים במאפייה בטווח התאריכים והמוצר הנבחרים.")

with col4:
    st.metric("ממוצע פריטים לעסקה", f"{avg_items_per_transaction:.2f}", help="הכמות הממוצעת של פריטים שנמכרו בכל עסקה בטווח התאריכים והמוצר הנבחרים.")

st.markdown("---")

# --- גרפים (מבוססים על df_filtered) ---

# גרף 1: 10 הפריטים הנמכרים ביותר
st.subheader("🔝 10 הפריטים הנמכרים ביותר")
top_items = df_filtered['Item'].value_counts().head(10).reset_index()
top_items.columns = ['Item', 'Count']

fig1 = px.bar(top_items, x='Item', y='Count',
              title="🏆 Top 10 Bestselling Bakery Items",
              text='Count',
              color_discrete_sequence=['#D2691E'], # צבע שוקולד
              labels={'Count': 'מספר מכירות', 'Item': 'פריט'})

st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# --- טבלה חדשה: מוצרים הנמכרים יחד עם קפה (מבוסס על df_filtered) ---
st.subheader("☕ מוצרים הנקנים לרוב עם קפה")

if st.session_state.selected_item == "כל המוצרים" or st.session_state.selected_item == "Coffee":
    if 'Coffee' in df_filtered['Item'].unique():
        coffee_transactions = df_filtered[df_filtered['Item'] == 'Coffee']['Transaction'].unique()
        df_coffee_transactions = df_filtered[df_filtered['Transaction'].isin(coffee_transactions)]
        items_with_coffee = df_coffee_transactions[df_coffee_transactions['Item'] != 'Coffee']['Item']

        if not items_with_coffee.empty:
            top_items_with_coffee_df = items_with_coffee.value_counts().head(10).reset_index()
            top_items_with_coffee_df.columns = ['מוצר', 'כמות מכירות עם קפה']

            top_items_with_coffee_df = pd.merge(top_items_with_coffee_df, total_item_sales,
                                                left_on='מוצר', right_on='Item', how='left')
            top_items_with_coffee_df = top_items_with_coffee_df.drop(columns='Item')

            # --- שינוי כאן: הצגת אחוזים ללא נקודה עשרונית + סימן % ---
            top_items_with_coffee_df['שיעור מכירות עם קפה (%)'] = (
                (top_items_with_coffee_df['כמות מכירות עם קפה'] / top_items_with_coffee_df['TotalSales']) * 100
            ).round(0).astype(int).astype(str) + '%' # <--- השינוי כאן: המרה לסטרינג והוספת %

            top_items_with_coffee_df.rename(columns={'TotalSales': 'סה"כ מכירות מוצר'}, inplace=True)

            display_columns_order = ['מוצר', 'כמות מכירות עם קפה', 'סה"כ מכירות מוצר', 'שיעור מכירות עם קפה (%)']
            st.table(top_items_with_coffee_df[display_columns_order])
            st.info("💡 טבלה זו מציגה את 10 המוצרים הנמכרים ביותר יחד עם קפה, כולל סך מכירותיהם ושיעור המכירות עם קפה. הנתונים מסוננים לפי טווח התאריכים הנבחר.")
        else:
            st.info("אין נתונים על פריטים אחרים שנמכרו יחד עם קפה בטווח התאריכים או עבור המוצר הנבחר.")
    else:
        st.warning("⚠️ הפריט 'Coffee' לא נמצא בנתונים בטווח התאריכים או עבור המוצר הנבחר, לכן לא ניתן להציג את המוצרים הנמכרים איתו.")
else:
    st.info("טבלת 'מוצרים הנקנים לרוב עם קפה' מוצגת רק כאשר 'כל המוצרים' נבחר או כאשר 'Coffee' נבחר כמוצר ספציפי.")


st.markdown("---")

# גרף 2: התפלגות מכירות לפי שעה ביום
st.subheader("⏰ התפלגות מכירות לפי שעה ביום")
df_filtered['Hour'] = df_filtered['date_time'].dt.hour
hourly = df_filtered.groupby('Hour').size().reset_index(name='Count')
all_hours = pd.DataFrame({'Hour': range(24)})
hourly = pd.merge(all_hours, hourly, on='Hour', how='left').fillna(0)

fig2 = px.bar(hourly, x='Hour', y='Count',
              title="Transactions per Hour of Day",
              text='Count',
              color_discrete_sequence=['#FFA07A'], # צבע סלמון בהיר
              labels={'Count': 'מספר עסקאות', 'Hour': 'שעה'})
fig2.update_traces(texttemplate='%{text}', textposition='outside')
fig2.update_layout(xaxis_title="שעה ביום", yaxis_title="מספר עסקאות")
fig2.update_yaxes(range=[0, hourly['Count'].max() * 1.1]) 
fig2.update_xaxes(dtick=1, range=[-0.5, 23.5])

st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# גרף 3: מגמת עסקאות לפי חודש (שנה-חודש)
st.subheader("📊 מגמת עסקאות חודשית")
df_filtered['YearMonth'] = df_filtered['date_time'].dt.to_period('M').astype(str)
monthly_transactions = df_filtered.groupby('YearMonth')['Transaction'].nunique().reset_index()
monthly_transactions.columns = ['YearMonth', 'UniqueTransactions']
monthly_transactions['YearMonth'] = pd.to_datetime(monthly_transactions['YearMonth'])
monthly_transactions = monthly_transactions.sort_values('YearMonth')
monthly_transactions['YearMonth'] = monthly_transactions['YearMonth'].dt.strftime('%Y-%m')

fig4 = px.line(monthly_transactions, x='YearMonth', y='UniqueTransactions',
                title="Total Transactions Over Time (Monthly)",
                labels={'YearMonth': 'שנה-חודש', 'UniqueTransactions': 'מספר עסקאות ייחודיות'},
                markers=True,
                line_shape='linear',
                color_discrete_sequence=['#8B4513'] # צבע חום אוכף
                )
fig4.update_layout(hovermode="x unified")
st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# גרף 4: התפלגות מכירות לפי חלק ביום (Daypart)
st.subheader("🌞 התפלגות מכירות לפי חלק ביום")
if 'Daypart' not in df_filtered.columns or df_filtered['Daypart'].empty:
    def get_daypart(hour):
        if 5 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 21:
            return 'Evening'
        else:
            return 'Night'
    df_filtered['Daypart'] = df_filtered['Hour'].apply(get_daypart)
    
if 'Daypart' in df_filtered.columns and not df_filtered['Daypart'].empty:
    daypart = df_filtered['Daypart'].value_counts().reset_index()
    daypart.columns = ['Daypart', 'Count']

    fig3 = px.pie(daypart, names='Daypart', values='Count',
                  title="Sales by Daypart",
                  hole=0.4,
                  color_discrete_sequence=px.colors.qualitative.Pastel, # נשאר פסטל
                  labels={'Count': 'מספר מכירות'})

    st.plotly_chart(fig3, use_container_width=True)
else:
    st.warning("⚠️ אין עמודת 'Daypart' או שהיא ריקה בנתונים המסוננים. דלג על גרף זה.")

st.markdown("---")

# --- פונקציה ליצירת דוח PDF ---
def generate_pdf_report(
    unique_transactions_val,
    total_items_sold_val,
    unique_items_val,
    avg_items_per_transaction_val,
    fig1_obj, fig2_obj, fig3_obj, fig4_obj,
    coffee_table_df
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []

    # כותרת הדוח
    Story.append(Paragraph("דוח מכירות מאפייה - סיכום", styles['h1']))
    Story.append(Spacer(1, 0.2 * inch))

    # מדדי מפתח (KPIs)
    Story.append(Paragraph("<b>מדדי מפתח:</b>", styles['h2']))
    Story.append(Paragraph(f"<b>סה\"כ עסקאות:</b> {unique_transactions_val}", styles['Normal']))
    Story.append(Paragraph(f"<b>סה\"כ פריטים שנמכרו:</b> {total_items_sold_val}", styles['Normal']))
    Story.append(Paragraph(f"<b>מספר פריטים ייחודיים:</b> {unique_items_val}", styles['Normal']))
    Story.append(Paragraph(f"<b>ממוצע פריטים לעסקה:</b> {avg_items_per_transaction_val:.2f}", styles['Normal']))
    Story.append(Spacer(1, 0.2 * inch))

    # טבלת מוצרים הנקנים עם קפה
    if not coffee_table_df.empty:
        Story.append(Paragraph("<b>מוצרים הנקנים לרוב עם קפה:</b>", styles['h2']))
        # ודא שהעמודה מוצגת כאחוז שלם ב-PDF גם כן
        coffee_table_df_for_pdf = coffee_table_df.copy()
        # הערה: עמודת 'שיעור מכירות עם קפה (%)' כבר מכילה את ה-% מהלוגיקה של ה-DataFrame למטה.
        # לכן כאן רק נמיר אותה לסטרינג אם היא לא כבר כזו, כדי לוודא תאימות לטבלה של reportlab.
        coffee_table_df_for_pdf['שיעור מכירות עם קפה (%)'] = coffee_table_df_for_pdf['שיעור מכירות עם קפה (%)'].astype(str)

        data = [coffee_table_df_for_pdf.columns.tolist()] + coffee_table_df_for_pdf.values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        Story.append(table)
        Story.append(Spacer(1, 0.2 * inch))

    # הוספת גרפים כתמונות
    chart_objects = [
        ("10 הפריטים הנמכרים ביותר", fig1_obj),
        ("התפלגות מכירות לפי שעה ביום", fig2_obj),
        ("מגמת עסקאות חודשית", fig4_obj), # fig4 הוא גרף מגמת העסקאות
        ("התפלגות מכירות לפי חלק ביום", fig3_obj) # fig3 הוא גרף ה-Daypart
    ]

    for title, fig_obj in chart_objects:
        if fig_obj: # ודא שהגרף קיים (במקרה של Daypart שלא תמיד מוצג)
            img_buffer = io.BytesIO()
            fig_obj.write_image(img_buffer, format="png", width=800, height=500, scale=2) # הגדל רזולוציה
            img_buffer.seek(0)
            
            img = Image(img_buffer)
            img.drawHeight = 4 * inch # התאמת גובה התמונה ב-PDF
            img.drawWidth = 6 * inch  # התאמת רוחב התמונה ב-PDF
            
            Story.append(Paragraph(f"<b>{title}:</b>", styles['h2']))
            Story.append(img)
            Story.append(Spacer(1, 0.2 * inch))

    doc.build(Story)
    buffer.seek(0)
    return buffer

# --- כפתור הורדת דוח PDF בסרגל הצד ---
with st.sidebar:
    st.markdown("---")
    st.subheader("🗂️ אפשרויות ייצוא")

    # הכנת נתונים עבור טבלת הקפה ב-PDF (אם רלוונטי)
    pdf_coffee_table_df = pd.DataFrame() # ברירת מחדל ריקה
    if st.session_state.selected_item == "כל המוצרים" or st.session_state.selected_item == "Coffee":
        if 'Coffee' in df_filtered['Item'].unique():
            coffee_transactions = df_filtered[df_filtered['Item'] == 'Coffee']['Transaction'].unique()
            df_coffee_transactions = df_filtered[df_filtered['Transaction'].isin(coffee_transactions)]
            items_with_coffee = df_coffee_transactions[df_coffee_transactions['Item'] != 'Coffee']['Item']
            if not items_with_coffee.empty:
                pdf_coffee_table_df = items_with_coffee.value_counts().head(10).reset_index()
                pdf_coffee_table_df.columns = ['מוצר', 'כמות מכירות עם קפה']
                pdf_coffee_table_df = pd.merge(pdf_coffee_table_df, total_item_sales,
                                                left_on='מוצר', right_on='Item', how='left')
                pdf_coffee_table_df = pdf_coffee_table_df.drop(columns='Item')
                # --- שינוי כאן: הצגת אחוזים ללא נקודה עשרונית + סימן % גם עבור ה-PDF ---
                pdf_coffee_table_df['שיעור מכירות עם קפה (%)'] = (
                    (pdf_coffee_table_df['כמות מכירות עם קפה'] / pdf_coffee_table_df['TotalSales']) * 100
                ).round(0).astype(int).astype(str) + '%' # <--- השינוי כאן
                pdf_coffee_table_df.rename(columns={'TotalSales': 'סה"כ מכירות מוצר'}, inplace=True)
                pdf_coffee_table_df = pdf_coffee_table_df[['מוצר', 'כמות מכירות עם קפה', 'סה"כ מכירות מוצר', 'שיעור מכירות עם קפה (%)']]


    # יצירת הדוח PDF כאשר הכפתור נלחץ
    if st.sidebar.button("הורד דוח PDF"):
        with st.spinner("יוצר דוח PDF..."):
            pdf_buffer = generate_pdf_report(
                unique_transactions,
                total_items_sold,
                df_filtered['Item'].nunique(),
                avg_items_per_transaction,
                fig1, fig2, fig3, fig4, # העברת אובייקטי הגרפים
                pdf_coffee_table_df # העברת הדאטהפריים של טבלת הקפה
            )
        st.sidebar.download_button(
            label="לחץ כאן להורדת הדוח",
            data=pdf_buffer,
            file_name="Bakery_Sales_Report.pdf",
            mime="application/pdf"
        )
        st.sidebar.success("דוח PDF נוצר בהצלחה!")


st.info("🚀 הדשבורד עודכן בהצלחה! המשך לשפר ולנתח את נתוני המאפייה שלך.")
