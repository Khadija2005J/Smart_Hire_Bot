import os
from datetime import datetime
from typing import Dict, Optional
from fpdf import FPDF


class ContractPDF(FPDF):
    """Classe personnalisée pour générer des PDFs de contrats"""
    
    def __init__(self):
        super().__init__()
        self.WIDTH = 210
        self.HEIGHT = 297
        
    def header(self):
        # En-tête avec le titre
        self.set_font("Arial", "B", 14)
        self.ln(10)
        
    def footer(self):
        # Pied de page
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
        
    def add_title(self, title: str):
        """Ajouter un titre au document"""
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, title, ln=True, align="C")
        self.ln(5)
        
    def add_section_title(self, title: str):
        """Ajouter un titre de section"""
        self.set_font("Arial", "B", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, title, ln=True)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        
    def add_text(self, text: str, size: int = 10, bold: bool = False):
        """Ajouter du texte au document avec wrapping automatique"""
        self.set_font("Arial", "B" if bold else "", size)
        self.set_text_color(0, 0, 0)
        
        # Utiliser multi_cell avec une largeur correcte (170 pour laisser des marges)
        self.multi_cell(170, 5, text)
        
    def add_paragraph(self, text: str, size: int = 10):
        """Ajouter un paragraphe avec espacement"""
        self.add_text(text, size)
        self.ln(2)


def generate_contract(
    candidate: Dict,
    contract_type: str,
    salary: int,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    company_name: str = "Smart-Hire SAS",
    company_address: str = "123 Avenue de l'Innovation, 75001 Paris"
) -> str:
    """
    Génère un contrat de travail au format PDF.
    
    Args:
        candidate: Dictionnaire contenant les informations du candidat
        contract_type: Type de contrat (CDI, CDD, Stage, Freelance)
        salary: Salaire annuel brut
        start_date: Date de début du contrat
        end_date: Date de fin (pour CDD)
        company_name: Nom de l'entreprise
        company_address: Adresse de l'entreprise
    
    Returns:
        Chemin du fichier de contrat généré (PDF)
    """
    
    # Créer le dossier contracts s'il n'existe pas
    os.makedirs("contracts", exist_ok=True)
    
    # Nom du fichier
    filename = f"contracts/contrat_{candidate['nom']}_{candidate['prenom']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    # Informations du candidat
    candidate_name = f"{candidate['nom']} {candidate['prenom']}"
    candidate_email = candidate['email']
    candidate_position = candidate.get('poste', 'Poste à définir')
    
    # Formater les dates
    start_date_str = start_date.strftime("%d/%m/%Y")
    contract_date_str = datetime.now().strftime("%d/%m/%Y")
    
    # Créer le PDF
    pdf = ContractPDF()
    pdf.add_page()
    
    # Construire le contrat selon le type
    if contract_type == "CDI":
        _generate_cdi_contract_pdf(
            pdf, candidate_name, candidate_email, candidate_position,
            salary, start_date_str, contract_date_str,
            company_name, company_address
        )
    elif contract_type == "CDD":
        end_date_str = end_date.strftime("%d/%m/%Y") if end_date else "A definir"
        _generate_cdd_contract_pdf(
            pdf, candidate_name, candidate_email, candidate_position,
            salary, start_date_str, end_date_str, contract_date_str,
            company_name, company_address
        )
    elif contract_type == "Stage":
        _generate_internship_contract_pdf(
            pdf, candidate_name, candidate_email, candidate_position,
            salary, start_date_str, contract_date_str,
            company_name, company_address
        )
    else:  # Freelance
        _generate_freelance_contract_pdf(
            pdf, candidate_name, candidate_email, candidate_position,
            salary, start_date_str, contract_date_str,
            company_name, company_address
        )
    
    # Sauvegarder le PDF
    pdf.output(filename)
    
    return filename


def _generate_cdi_contract_pdf(
    pdf: ContractPDF, candidate_name: str, candidate_email: str, position: str,
    salary: int, start_date: str, contract_date: str,
    company_name: str, company_address: str
):
    """Génère un contrat CDI en PDF"""
    
    pdf.add_title("CONTRAT DE TRAVAIL A DUREE INDET. (CDI)")
    pdf.add_text(f"Date: {contract_date}")
    pdf.add_text(f"Ref: CDI-{datetime.now().strftime('%Y%m%d')}")
    pdf.ln(3)
    
    pdf.add_section_title("PARTIES AU CONTRAT")
    pdf.add_text(f"L'Entreprise: {company_name}", bold=True)
    pdf.add_text(f"Adresse: {company_address}")
    pdf.ln(2)
    
    pdf.add_text(f"Le Salarie: {candidate_name}", bold=True)
    pdf.add_text(f"Email: {candidate_email}")
    pdf.ln(3)
    
    pdf.add_section_title("ARTICLE 1 - ENGAGEMENT")
    txt = f"L'Employeur engage le Salarie en qualite de {position}, a compter du {start_date}. Le contrat est conclu pour une duree indeteminee."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 2 - FONCTIONS")
    txt = f"Le Salarie exercera les fonctions de {position}. Il sera charge notamment de: participer aux projets, contribuer a l'amelioration continue, collaborer avec les equipes, respecter les directives."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 3 - REMUNERATION")
    txt = f"En contrepartie, le Salarie percevra une remuneration brute annuelle de {salary:,} euros. Soit un salaire mensuel brut de {salary/12:,.2f} euros. Versement mensuel par virement bancaire."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 4 - DUREE DU TRAVAIL")
    txt = "La duree hebdomadaire est fixee a 35 heures du lundi au vendredi. Horaires: 9h00-17h00 avec 1h de pause."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 5 - PERIODE D'ESSAI")
    txt = "Le contrat est conclu sous reserve d'une periode d'essai de 3 mois, renouvelable une fois. Il pourra etre rompu sans indemnite pendant cette periode."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 6 - CONGES PAYES")
    txt = "Le Salarie beneficie de conges payes conformement a la legislation, soit 2,5 jours ouvrables par mois."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 7 - CONFIDENTIALITE")
    txt = "Le Salarie s'engage a observer la plus stricte confidentialite sur les informations relatives au travail."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 8 - CLAUSE DE NON-CONCURRENCE")
    txt = "Pendant 12 mois apres la cessation du contrat, le Salarie s'interdit d'exercer une activite concurrente."
    pdf.add_paragraph(txt)
    
    pdf.ln(10)
    pdf.add_text(f"A Paris, le {contract_date}")
    pdf.ln(5)
    pdf.add_text("L'Employeur                     Le Salarie")
    pdf.ln(8)
    pdf.add_text("Signature:                     Signature:")


def _generate_cdd_contract_pdf(
    pdf: ContractPDF, candidate_name: str, candidate_email: str, position: str,
    salary: int, start_date: str, end_date: str, contract_date: str,
    company_name: str, company_address: str
):
    """Génère un contrat CDD en PDF"""
    
    pdf.add_title("CONTRAT DE TRAVAIL A DUREE DETERMINE (CDD)")
    pdf.add_text(f"Date: {contract_date}")
    pdf.add_text(f"Ref: CDD-{datetime.now().strftime('%Y%m%d')}")
    pdf.ln(3)
    
    pdf.add_section_title("PARTIES AU CONTRAT")
    pdf.add_text(f"L'Entreprise: {company_name}", bold=True)
    pdf.add_text(f"Adresse: {company_address}")
    pdf.ln(2)
    
    pdf.add_text(f"Le Salarie: {candidate_name}", bold=True)
    pdf.add_text(f"Email: {candidate_email}")
    pdf.ln(3)
    
    pdf.add_section_title("ARTICLE 1 - ENGAGEMENT")
    txt = f"L'Employeur engage le Salarie en qualite de {position}. Le contrat est conclu pour une duree determinee du {start_date} au {end_date}."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 2 - REMUNERATION")
    txt = f"Remuneration brute annuelle: {salary:,} euros. Salaire mensuel brut: {salary/12:,.2f} euros."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 3 - DUREE DU TRAVAIL")
    txt = "Duree hebdomadaire: 35 heures. Horaires: Lundi au Vendredi, 9h00-17h00."
    pdf.add_paragraph(txt)
    
    pdf.add_section_title("ARTICLE 4 - FIN DE CONTRAT")
    txt = "A l'echeance du terme, le Salarie percevra une indemnite de fin de contrat egale a 10% de la remuneration brute totale versee."
    pdf.add_paragraph(txt)
    
    pdf.ln(10)
    pdf.add_text(f"A Paris, le {contract_date}")
    pdf.ln(5)
    pdf.add_text("L'Employeur                     Le Salarie")
    pdf.ln(8)
    pdf.add_text("Signature:                     Signature:")


def _generate_internship_contract_pdf(
    pdf: ContractPDF, candidate_name: str, candidate_email: str, position: str,
    salary: int, start_date: str, contract_date: str,
    company_name: str, company_address: str
):
    """Génère une convention de stage en PDF"""
    
    pdf.add_title("CONVENTION DE STAGE")
    pdf.add_text(f"Date: {contract_date}")
    pdf.add_text(f"Ref: STAGE-{datetime.now().strftime('%Y%m%d')}")
    pdf.ln(3)
    
    pdf.add_section_title("PARTIES AU CONTRAT")
    pdf.add_text(f"L'Entreprise: {company_name}", bold=True)
    pdf.add_text(f"Adresse: {company_address}")
    pdf.ln(2)
    
    pdf.add_text(f"Le Stagiaire: {candidate_name}", bold=True)
    pdf.add_text(f"Email: {candidate_email}")
    pdf.ln(3)
    
    pdf.add_section_title("DETAILS DU STAGE")
    txt = f"Poste: {position}\nDate de debut: {start_date}\nDuree: 6 mois\nGratification mensuelle: {salary/12:,.2f} euros"
    pdf.add_paragraph(txt)


def _generate_freelance_contract_pdf(
    pdf: ContractPDF, candidate_name: str, candidate_email: str, position: str,
    salary: int, start_date: str, contract_date: str,
    company_name: str, company_address: str
):
    """Génère un contrat freelance en PDF"""
    
    pdf.add_title("CONTRAT DE PRESTATION DE SERVICE")
    pdf.add_text(f"Date: {contract_date}")
    pdf.add_text(f"Ref: FREELANCE-{datetime.now().strftime('%Y%m%d')}")
    pdf.ln(3)
    
    pdf.add_section_title("PARTIES AU CONTRAT")
    pdf.add_text(f"Le Client: {company_name}", bold=True)
    pdf.add_text(f"Adresse: {company_address}")
    pdf.ln(2)
    
    pdf.add_text(f"Le Prestataire: {candidate_name}", bold=True)
    pdf.add_text(f"Email: {candidate_email}")
    pdf.ln(3)
    
    pdf.add_section_title("DETAILS DE LA MISSION")
    txt = f"Mission: {position}\nDate de debut: {start_date}\nRemuneration: {salary:,} euros HT par an"
    pdf.add_paragraph(txt)
