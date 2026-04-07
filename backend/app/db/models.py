import enum
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, Float, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AuthorshipRole(str, enum.Enum):
    FIRST_AUTHOR = "FIRST_AUTHOR"
    CO_AUTHOR = "CO_AUTHOR"
    LAST_AUTHOR = "LAST_AUTHOR"
    CORRESPONDING_AUTHOR = "CORRESPONDING_AUTHOR"

class EvidenceStrength(str, enum.Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    linkedin_url = Column(String, nullable=True)
    nationality = Column(String, nullable=True)
    universities = Column(Text, nullable=True)
    cv_filename = Column(String, nullable=False)
    cv_filepath = Column(String, nullable=False)
    cv_raw_text = Column(Text, nullable=True)
    status = Column(Enum(ProcessingStatus, name="processing_status"), default=ProcessingStatus.PENDING)
    overall_summary = Column(Text, nullable=True)
    overall_score = Column(Float, nullable=True)

    # structured analysis outputs (stored as json text)
    education_json = Column(Text, nullable=True)
    experience_json = Column(Text, nullable=True)
    research_json = Column(Text, nullable=True)
    missing_info_json = Column(Text, nullable=True)
    missing_info_email = Column(Text, nullable=True)
    # deep publication analysis cache (filled by /analysis/candidate/{id}/publications)
    publication_analysis_json = Column(Text, nullable=True)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class Publication(Base):
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    pub_type = Column(String, nullable=True)
    title = Column(Text, nullable=True)
    authors_raw = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    authorship_role = Column(Enum(AuthorshipRole, name="authorship_role"), nullable=True)
    candidate_author_position = Column(Integer, nullable=True)
    quality_note = Column(Text, nullable=True)


class JournalDetails(Base):
    __tablename__ = "journal_details"

    id = Column(Integer, primary_key=True, index=True)
    publication_id = Column(Integer, ForeignKey("publications.id"), nullable=False)
    journal_name = Column(String, nullable=True)
    issn = Column(String, nullable=True)
    is_wos_indexed = Column(Boolean, nullable=True)
    impact_factor = Column(Float, nullable=True)
    is_scopus_indexed = Column(Boolean, nullable=True)
    quartile = Column(String, nullable=True)
    is_predatory = Column(Boolean, nullable=True)


class ConferenceDetails(Base):
    __tablename__ = "conference_details"

    id = Column(Integer, primary_key=True, index=True)
    publication_id = Column(Integer, ForeignKey("publications.id"), nullable=False)
    conference_name = Column(String, nullable=True)
    proceedings_title = Column(Text, nullable=True)
    core_rank = Column(String, nullable=True)
    is_a_star = Column(Boolean, nullable=True)
    series_edition = Column(String, nullable=True)
    is_scopus_indexed = Column(Boolean, nullable=True)
    is_ieee_xplore = Column(Boolean, nullable=True)
    is_springer = Column(Boolean, nullable=True)
    is_acm = Column(Boolean, nullable=True)
    other_indexing = Column(String, nullable=True)


class PublicationCoAuthor(Base):
    __tablename__ = "publication_co_authors"

    id = Column(Integer, primary_key=True, index=True)
    publication_id = Column(Integer, ForeignKey("publications.id"), nullable=False)
    co_author_name = Column(String, nullable=True)
    author_position = Column(Integer, nullable=True)
    is_recurring = Column(Boolean, nullable=True)


class CoauthorAnalysis(Base):
    __tablename__ = "coauthor_analysis"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    total_unique_coauthors = Column(Integer, nullable=True)
    avg_coauthors_per_paper = Column(Float, nullable=True)
    max_coauthors_in_paper = Column(Integer, nullable=True)
    recurring_collaborators = Column(JSON, nullable=True)
    most_frequent_collaborator = Column(String, nullable=True)
    collaboration_diversity_score = Column(Float, nullable=True)
    has_student_collaborations = Column(Boolean, nullable=True)
    has_international_collaborations = Column(Boolean, nullable=True)
    collaboration_summary = Column(Text, nullable=True)


class TopicVariability(Base):
    __tablename__ = "topic_variability"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    dominant_topic = Column(String, nullable=True)
    diversity_score = Column(Float, nullable=True)
    topic_clusters = Column(JSON, nullable=True)
    topic_trend = Column(Text, nullable=True)
    variability_summary = Column(Text, nullable=True)


class Patent(Base):
    __tablename__ = "patents"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    patent_number = Column(String, nullable=True)
    patent_title = Column(Text, nullable=True)
    filing_date = Column(String, nullable=True)
    inventors_raw = Column(Text, nullable=True)
    country_of_filing = Column(String, nullable=True)
    verification_link = Column(String, nullable=True)
    candidate_role = Column(String, nullable=True)
    is_verified = Column(Boolean, nullable=True)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    book_title = Column(Text, nullable=True)
    authors_raw = Column(Text, nullable=True)
    isbn = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    publishing_year = Column(Integer, nullable=True)
    online_link = Column(String, nullable=True)
    authorship_role = Column(String, nullable=True)
    publisher_credibility_note = Column(Text, nullable=True)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    skill_name = Column(String, nullable=True)
    skill_category = Column(String, nullable=True)
    evidence_strength = Column(Enum(EvidenceStrength, name="evidence_strength"), nullable=True)
    supported_by_experience = Column(Boolean, nullable=True)
    supported_by_publications = Column(Boolean, nullable=True)
    evidence_note = Column(Text, nullable=True)
    job_relevance_score = Column(Float, nullable=True)


class SupervisedStudent(Base):
    __tablename__ = "supervised_students"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    student_name = Column(String, nullable=True)
    degree_level = Column(String, nullable=True)
    supervision_role = Column(String, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    thesis_title = Column(Text, nullable=True)
    joint_publications_count = Column(Integer, nullable=True)


class MissingInfoEmail(Base):
    __tablename__ = "missing_info_emails"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    missing_fields = Column(JSON, nullable=True)
    email_subject = Column(String, nullable=True)
    email_body = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    is_sent = Column(Boolean, nullable=True)


class EducationRecord(Base):
    __tablename__ = "education_records"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    degree_level = Column(String, nullable=True)
    degree_title = Column(String, nullable=True)
    specialization = Column(String, nullable=True)
    institution_name = Column(String, nullable=True)
    board_or_affiliation = Column(String, nullable=True)
    raw_result = Column(String, nullable=True)
    cgpa_normalized = Column(Float, nullable=True)
    percentage_normalized = Column(Float, nullable=True)
    year_start = Column(Integer, nullable=True)
    year_end = Column(Integer, nullable=True)
    the_ranking = Column(Integer, nullable=True)
    qs_ranking = Column(Integer, nullable=True)
    ranking_unavailable = Column(Boolean, nullable=True)
    performance_note = Column(Text, nullable=True)


class ExperienceRecord(Base):
    __tablename__ = "experience_records"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_title = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    is_current = Column(Boolean, nullable=True)
    responsibilities = Column(Text, nullable=True)
    career_level = Column(String, nullable=True)
    progression_note = Column(Text, nullable=True)


class EducationGap(Base):
    __tablename__ = "education_gaps"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    gap_between = Column(String, nullable=True)
    gap_duration_months = Column(Integer, nullable=True)
    is_justified = Column(Boolean, nullable=True)
    justification_note = Column(Text, nullable=True)


class ExperienceGap(Base):
    __tablename__ = "experience_gaps"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    gap_type = Column(String, nullable=True)
    gap_description = Column(Text, nullable=True)
    gap_duration_months = Column(Integer, nullable=True)
    is_justified = Column(Boolean, nullable=True)
    justification_note = Column(Text, nullable=True)
    is_suspicious = Column(Boolean, nullable=True)
