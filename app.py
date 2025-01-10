import os
import mysql.connector
from PIL import Image, ImageOps
import streamlit as st
import easyocr
import re


DB_CONFIG = {
    'host': 'localhost',  
    'user': 'root',       
    'password': 'Mohamed', 
    'database': 'bizcardx' 
}


def connect_to_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except mysql.connector.Error as e:
        st.error(f"Database connection failed: {e}")
    return None


def extract_information(image_path):
    reader = easyocr.Reader(['en'])
    
    
    image = Image.open(image_path)
    grayscale_image = ImageOps.grayscale(image)
    resized_image = grayscale_image.resize((800, 600))
    resized_image.save(image_path)
    
    
    result = reader.readtext(image_path)
    
    extracted_info = {}
    indian_states = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", 
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", 
        "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", 
        "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", 
        "West Bengal"
    ]
    tamil_nadu_districts = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kanchipuram",
    "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
    "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukottai",
    "Ramanathapuram", "Ranipet", "Salem", "Sivagangai", "Tenkasi",
    "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli",
    "Tirupattur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur",
    "Vellore", "Viluppuram", "Virudhunagar"
]




    for _, text, _ in result:
        text = text.strip()

        if "@" in text and "." in text:
            extracted_info['email_address'] = text

        elif text.isdigit() and len(text) >= 10:
            extracted_info['mobile_number'] = text

        elif any(keyword in text.lower() for keyword in ["inc", "corp", "company", "llc", "ltd"]):
            extracted_info['company_name'] = text

        elif "www." in text.lower() or ".com" in text.lower():
            extracted_info['website_url'] = text

        elif len(text.split()) == 1 and text.isalpha():
            extracted_info['card_holder_name'] = text
            
        elif "street" in text.lower() or "," in text:
            extracted_info['area'] = text
        
        elif re.match(r'\d{6}', text):
            extracted_info['pin_code'] = text
        
        elif any(state.lower() in text.lower() for state in indian_states):
            extracted_info['state'] = text.strip()
        
        elif "india" in text.lower():
            extracted_info['country'] = text
        elif any(city.lower() in text.lower() for city in tamil_nadu_districts):
            extracted_info['city'] = text.strip()

    return extracted_info


def main():
    st.title("BizCardX: Business Card Data Extraction")
    menu = ["Upload", "View", "Update", "Delete"]
    choice = st.sidebar.selectbox("Menu", menu)
    conn = connect_to_db()
    if not conn:
        st.error("Unable to connect to the database.")
        return
    cursor = conn.cursor()

    if choice == "Upload":
        st.subheader("Upload a Business Card")
        image_file = st.file_uploader("Upload an Image", type=["jpg", "png", "jpeg"])
        if image_file:
            image_path = os.path.join("uploaded_images", image_file.name)
            os.makedirs("uploaded_images", exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(image_file.read())

            st.image(Image.open(image_path), caption="Uploaded Image", use_container_width=True)
            extracted_data = extract_information(image_path)
            st.write("Extracted Data:", extracted_data)

            if st.button("Save to Database"):
                query = """
                INSERT INTO business_cards (
                    company_name, card_holder_name, designation, mobile_number, 
                    email_address, website_url, area, city, state, pin_code, image_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    extracted_data.get('company_name', ''),
                    extracted_data.get('card_holder_name', ''),
                    extracted_data.get('designation', ''),
                    extracted_data.get('mobile_number', ''),
                    extracted_data.get('email_address', ''),
                    extracted_data.get('website_url', ''),
                    extracted_data.get('area', ''),
                    extracted_data.get('city', ''),
                    extracted_data.get('state', ''),
                    extracted_data.get('pin_code', ''),
                    image_path
                )
                try:
                    cursor.execute(query, values)
                    conn.commit()
                    st.success("Data saved successfully!")
                except mysql.connector.Error as e:
                    st.error(f"Failed to save data: {e}")

    elif choice == "View":
        st.subheader("View All Records")
        cursor.execute("SELECT * FROM business_cards")
        data = cursor.fetchall()
        if data:
            for row in data:
                st.write(dict(zip([desc[0] for desc in cursor.description], row)))
        else:
            st.warning("No records found.")

    elif choice == "Update":
        st.subheader("Update a Record")
        card_id = st.number_input("Enter ID to Update", min_value=1, step=1)
        cursor.execute("SELECT * FROM business_cards WHERE id=%s", (card_id,))
        record = cursor.fetchone()
        if record:
            company_name = st.text_input("Company Name", record[1])
            mobile_number = st.text_input("Mobile Number", record[4])
            if st.button("Update"):
                try:
                    cursor.execute("""
                    UPDATE business_cards 
                    SET company_name=%s, mobile_number=%s 
                    WHERE id=%s
                    """, (company_name, mobile_number, card_id))
                    conn.commit()
                    st.success("Record updated successfully!")
                except mysql.connector.Error as e:
                    st.error(f"Failed to update record: {e}")
        else:
            st.warning("Record not found.")

    elif choice == "Delete":
        st.subheader("Delete a Record")
        card_id = st.number_input("Enter ID to Delete", min_value=1, step=1)
        if st.button("Delete"):
            try:
                cursor.execute("DELETE FROM business_cards WHERE id=%s", (card_id,))
                conn.commit()
                st.success("Record deleted successfully!")
            except mysql.connector.Error as e:
                st.error(f"Failed to delete record: {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
