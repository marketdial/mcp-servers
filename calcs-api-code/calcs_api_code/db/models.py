"""
SQLAlchemy models for Calcs API test creation.

These are simplified models that mirror the web-api database schema,
providing just enough structure for test creation operations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============================================================================
# Enums (matching web-api)
# ============================================================================

class TestStatusEnum(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    READY_TO_RUN = "READY_TO_RUN"
    IN_MARKET = "IN_MARKET"
    COMPLETE = "COMPLETE"
    ARCHIVED = "ARCHIVED"


class TestVisibilityTypeEnum(str, Enum):
    TEST = "TEST"
    CHART = "CHART"


class CalcStatusEnum(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class TestGraphTypeEnum(str, Enum):
    AVRO = "AVRO"
    JSON = "JSON"


class TestTagTypeEnum(str, Enum):
    POPULATION_INCLUDE = "POPULATION_INCLUDE"
    POPULATION_EXCLUDE = "POPULATION_EXCLUDE"
    TREATMENT_INCLUDE = "TREATMENT_INCLUDE"
    TREATMENT_EXCLUDE = "TREATMENT_EXCLUDE"
    CONTROL_INCLUDE = "CONTROL_INCLUDE"
    CONTROL_EXCLUDE = "CONTROL_EXCLUDE"


class MetricTypeEnum(str, Enum):
    SALES = "SALES"
    UNITS = "UNITS"
    TRANSACTIONS = "TRANSACTIONS"
    MARGIN = "MARGIN"
    BASKET_SIZE = "BASKET_SIZE"
    FOOT_TRAFFIC = "FOOT_TRAFFIC"
    CONVERSION = "CONVERSION"


class MetricMeasurementTypeEnum(str, Enum):
    SITE = "SITE"
    CUSTOMER = "CUSTOMER"


class SiteStatusEnum(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"


# ============================================================================
# Core Models
# ============================================================================

class User(Base):
    """User model - simplified for test creation."""
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    auth0_id: Mapped[Optional[str]] = mapped_column(String(255))

    def __repr__(self):
        return f"<User[{self.id}] {self.name}>"


class Site(Base):
    """Site (store) model."""
    __tablename__ = "dim_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_client_id: Mapped[Optional[str]] = mapped_column(String(255))
    site_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[str]] = mapped_column(String(50))
    testable: Mapped[bool] = mapped_column(Boolean, default=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    market: Mapped[Optional[str]] = mapped_column(String(255))

    def __repr__(self):
        return f"<Site[{self.id}] {self.site_client_id}>"


class SiteAttributes(Base):
    """Site attributes for sample matching."""
    __tablename__ = "app_site_attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_sites.id"))
    attribute_name: Mapped[str] = mapped_column(String(255))
    attribute_value_float: Mapped[Optional[float]] = mapped_column(Float)
    attribute_value_string: Mapped[Optional[str]] = mapped_column(String(255))
    attribute_value_int: Mapped[Optional[int]] = mapped_column(Integer)
    variable_type: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self):
        return f"<SiteAttributes[{self.id}] site:{self.site_id} {self.attribute_name}>"


class Tag(Base):
    """Tag model for filtering sites."""
    __tablename__ = "app_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("app_users.id"))
    date_created: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self):
        return f"<Tag[{self.id}] {self.text}>"


class Metric(Base):
    """Metric definition model."""
    __tablename__ = "app_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    measurement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    observation_level: Mapped[str] = mapped_column(String(50), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_response: Mapped[bool] = mapped_column(Boolean, nullable=False)
    uuid: Mapped[Optional[int]] = mapped_column(Integer, unique=True)

    def __repr__(self):
        return f"<Metric[{self.id}] {self.measurement_type} {self.type}>"


class Hierarchy(Base):
    """Product hierarchy model."""
    __tablename__ = "dim_hierarchies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    level: Mapped[Optional[int]] = mapped_column(Integer)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("dim_hierarchies.id"))

    def __repr__(self):
        return f"<Hierarchy[{self.id}] {self.name}>"


class Test(Base):
    """Main test model."""
    __tablename__ = "app_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic info
    test_name: Mapped[Optional[str]] = mapped_column(String(500))
    test_description: Mapped[Optional[str]] = mapped_column(Text)
    test_type: Mapped[Optional[str]] = mapped_column(String(100))
    test_visibility: Mapped[str] = mapped_column(String(50), default="TEST")

    # Status
    test_status: Mapped[Optional[str]] = mapped_column(String(50))
    calcs_status: Mapped[Optional[str]] = mapped_column(String(50))
    calcs_started: Mapped[Optional[datetime]] = mapped_column(DateTime)
    calcs_ended: Mapped[Optional[datetime]] = mapped_column(DateTime)
    impacts_status: Mapped[Optional[str]] = mapped_column(String(50))

    # Test configuration
    is_historic: Mapped[bool] = mapped_column(Boolean, default=False)
    is_market_based_samples: Mapped[bool] = mapped_column(Boolean, default=False)
    is_date_staggered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_repeat_controls: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metric configuration
    test_metric_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("app_metrics.id"))

    # Sample configuration
    site_count: Mapped[Optional[int]] = mapped_column(Integer)
    site_count_range: Mapped[Optional[int]] = mapped_column(Integer)
    rollout_group_count: Mapped[Optional[int]] = mapped_column(Integer)
    min_num_market: Mapped[Optional[int]] = mapped_column(Integer)
    max_num_market: Mapped[Optional[int]] = mapped_column(Integer)

    # Duration
    week_count: Mapped[Optional[int]] = mapped_column(Integer)
    pre_week_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Confidence/Lift
    anticipated_lift_prcnt: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    estimated_confidence: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    current_lift: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    current_confidence: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    # Sample quality scores
    representativeness: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    comparability: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    # User tracking
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("app_users.id"))
    date_created: Mapped[Optional[datetime]] = mapped_column(DateTime)
    date_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Other options
    exclude_sites_from_other_tests: Mapped[bool] = mapped_column(Boolean, default=True)
    overridden_test_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer))
    finished_cohort_pair_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer))

    # Transaction filters
    transaction_attribute_filter_condition: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Relationships
    cohorts: Mapped[List["TestCohort"]] = relationship("TestCohort", back_populates="test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Test[{self.id}] {self.test_name}>"


class TestCohort(Base):
    """Test cohort model (groups of site pairs with same dates)."""
    __tablename__ = "app_test_cohorts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tests.id", ondelete="CASCADE"))

    date_test_start: Mapped[Optional[date]] = mapped_column(Date)
    impl_week_count: Mapped[Optional[int]] = mapped_column(Integer)
    legacy_date_implementation_start: Mapped[Optional[date]] = mapped_column(Date)
    pre_blockout_week_count: Mapped[int] = mapped_column(Integer, default=0)
    test_blockout_week_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    test: Mapped["Test"] = relationship("Test", back_populates="cohorts")
    site_pairs: Mapped[List["TestSitePair"]] = relationship("TestSitePair", back_populates="cohort", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TestCohort[{self.id}] test:{self.test_id}>"


class TestSitePair(Base):
    """Treatment/control site pair model."""
    __tablename__ = "app_tests_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_test_cohorts.id", ondelete="CASCADE"))

    treatment_site_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_sites.id"))
    control_site_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("dim_sites.id"))

    # Match quality scores
    pair_lift: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    comparability: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    correlation: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    correlation2: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    similarity: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    # Relationships
    cohort: Mapped["TestCohort"] = relationship("TestCohort", back_populates="site_pairs")

    def __repr__(self):
        return f"<TestSitePair[{self.id}] T:{self.treatment_site_id} C:{self.control_site_id}>"


class DirectCategory(Base):
    """Direct product/category selection for a test."""
    __tablename__ = "app_tests_direct_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tests.id", ondelete="CASCADE"))
    name: Mapped[Optional[str]] = mapped_column(String(500))

    # Metric data
    average_sales: Mapped[Optional[float]] = mapped_column(Numeric(20, 4))
    standard_deviation: Mapped[Optional[float]] = mapped_column(Numeric(20, 4))
    site_coef: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    week_coef: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    def __repr__(self):
        return f"<DirectCategory[{self.id}] test:{self.test_id}>"


class DirectItemsAssociation(Base):
    """Association between direct category and items (hierarchies, products, etc.)."""
    __tablename__ = "app_tests_direct_items"

    direct_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_tests_direct_category.id"), primary_key=True
    )
    hierarchy_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("dim_hierarchies.id"))
    product_id: Mapped[Optional[int]] = mapped_column(Integer)
    product_set_id: Mapped[Optional[int]] = mapped_column(Integer)
    product_attribute_id: Mapped[Optional[int]] = mapped_column(Integer)


class TestTagAssociation(Base):
    """Association between tests and tags."""
    __tablename__ = "app_tests_tags_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tests.id", ondelete="CASCADE"))
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tags.id"))
    association_type: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return f"<TestTagAssociation test:{self.test_id} tag:{self.tag_id} type:{self.association_type}>"


class VariableSetWeightings(Base):
    """Variable set weightings for sample optimization."""
    __tablename__ = "app_variable_set_weightings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variable_set_id: Mapped[int] = mapped_column(Integer)
    variable_name: Mapped[str] = mapped_column(String(255))
    weight: Mapped[float] = mapped_column(Numeric(10, 4))
    variable_type: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self):
        return f"<VariableSetWeightings {self.variable_name}: {self.weight}>"


# ============================================================================
# Helper Functions
# ============================================================================

def create_all_tables(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(engine)


def get_test_status_value(status: str) -> str:
    """Convert status string to enum value."""
    try:
        return TestStatusEnum[status].value
    except KeyError:
        return status
