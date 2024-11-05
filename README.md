# Drug Interaction Dashboard

An interactive web application for exploring drug interactions, properties, and chemical characteristics powered by the ChEMBL database.

## 🌟 Features

### 1. Drug Search & Details
- **Smart Search**: Search for any drug in the ChEMBL database
- **Comprehensive Details**: View key drug information including:
  - Max phase
  - Therapeutic flag
  - Molecule type
  - First approval date
  - Administration routes (oral, parenteral, topical)
  - Black box warnings
  - Natural product status
  - First-in-class status
  - Chirality

### 2. Drug Properties Analysis
- **Chemical Properties**: Detailed view of drug properties including:
  - Molecular weight
  - LogP
  - Polar surface area (PSA)
  - Hydrogen bond donors/acceptors
  - Other physicochemical properties

### 3. Drug-likeness Analysis
- **Interactive Dashboard** featuring:
  - Molecular Weight Distribution
  - LogP vs Polar Surface Area plots
  - H-Bond Donors vs Acceptors visualization
  - Lipinski's Rule of 5 compliance charts
- **Downloadable Visualizations** in PNG format

### 4. Network Visualization
- **Interactive Network Graph** showing:
  - Drug-target interactions
  - Mechanism of action groupings
  - Color-coded relationships
- **Interactive Features**:
  - Zoom and pan capabilities
  - Node dragging
  - Hover tooltips
  - Network controls
- **Download Options** for network visualizations

## 🚀 Getting Started

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your database credentials:
   ```
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_HOST=your_host
   DB_PORT=1234
   DB_NAME=your_db
   ```

3. Never commit your `.env` file to version control!

### Prerequisites
- Python 3.8+
- PostgreSQL database with ChEMBL data
- Required Python packages (see requirements.txt)

### Installation
1. Clone the repository
