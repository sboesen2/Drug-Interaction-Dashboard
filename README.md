# Drug Interaction Dashboard 🧬

## Overview

The Drug Interaction Dashboard is an interactive web application that provides detailed insights into drug interactions, mechanisms of action, and chemical properties. Built using data from the ChEMBL database, this tool is designed for researchers, healthcare professionals, and pharmaceutical enthusiasts to explore and understand drug relationships and their properties.

## Features

### 🔍 Interactive Drug Search
- Real-time drug search functionality
- Auto-complete suggestions
- Filtering by drug phase and therapeutic flags

### 📊 Detailed Drug Information
- Comprehensive drug properties
- Chemical characteristics
- Approval status and development phase
- Administration routes
- Safety information (including black box warnings)

### 🕸️ Interactive Network Visualization
- Dynamic visualization of drug interactions
- Mechanism of action grouping
- Color-coded relationship mapping
- Zoom and pan capabilities
- Detailed tooltips for additional information

### 📈 Chemical Properties Analysis
- Molecular weight
- LogP values
- Hydrogen bond donors/acceptors
- Polar surface area
- Aromatic rings count
- Drug-likeness scores

## Technologies Used

### Backend
- **Database**: PostgreSQL (ChEMBL database)
- **API**: Python with SQLAlchemy
- **Data Processing**: Pandas, NetworkX

### Frontend
- **Framework**: Streamlit
- **Visualization**: Pyvis Network
- **Styling**: Custom CSS

### Development & Deployment
- **Version Control**: Git
- **Environment Management**: Docker
- **Dependency Management**: pip/requirements.txt

## Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Docker (optional)

### Installation

1. Clone the repository:
   
   ```bash
   git clone https://github.com/sboesen2/Drug-Interaction-Dashboard.git
   cd Drug-Interaction-Dashboard

2. Install dependencies

   ```bash
   pip install -r requirements.txt

3. Set up enviroment variables:
   - Set up environment variables by creating a .env file

```bash
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=your_host
DB_PORT=your_port
DB_NAME=your_database_name
```

4. Run the app


```bash
streamlit run streamlit.py
```


## Database Access

While the application code is open-source, the full ChEMBL database is not included in this repository due to size constraints. However, I am happy to share the database with anyone interested in learning or contributing to the project. Please reach out to me directly to discuss database access.

### Options for Database Setup:
1. Request access to our prepared database
2. Download the ChEMBL database directly from their website
3. Create a smaller test database using the provided schema

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Contact

For database access or any questions about the project, please feel free to reach out:

- GitHub Issues: [Create an Issue](https://github.com/sboesen2/Drug-Interaction-Dashboard/issues)
- Email: [Your Email]

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ChEMBL Database for providing the pharmaceutical data
- The Streamlit team for their excellent framework
- All contributors and users of this dashboard

---

**Note**: This is an educational and research tool. Always consult healthcare professionals for medical advice.












