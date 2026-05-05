EXPECTED_COLUMNS = (
    "asofdate",
    "program",
    "locationid",
    "borrname",
    "borrstreet",
    "borrcity",
    "borrstate",
    "borrzip",
    "bankname",
    "bankfdicnumber",
    "bankncuanumber",
    "bankstreet",
    "bankcity",
    "bankstate",
    "bankzip",
    "grossapproval",
    "sbaguaranteedapproval",
    "approvaldate",
    "approvalfy",
    "firstdisbursementdate",
    "processingmethod",
    "subprogram",
    "initialinterestrate",
    "fixedorvariableinterestind",
    "terminmonths",
    "naicscode",
    "naicsdescription",
    "franchisecode",
    "franchisename",
    "projectcounty",
    "projectstate",
    "sbadistrictoffice",
    "congressionaldistrict",
    "businesstype",
    "businessage",
    "loanstatus",
    "paidinfulldate",
    "chargeoffdate",
    "grosschargeoffamount",
    "revolverstatus",
    "jobssupported",
    "collateralind",
    "soldsecmrktind",
)

COLUMN_TYPES = {
    "asofdate": "date",
    "program": "string",
    "locationid": "string",
    "borrname": "string",
    "borrstreet": "string",
    "borrcity": "string",
    "borrstate": "string",
    "borrzip": "string",
    "bankname": "string",
    "bankfdicnumber": "string",
    "bankncuanumber": "string",
    "bankstreet": "string",
    "bankcity": "string",
    "bankstate": "string",
    "bankzip": "string",
    "grossapproval": "integer",
    "sbaguaranteedapproval": "integer",
    "approvaldate": "date",
    "approvalfy": "integer",
    "firstdisbursementdate": "date",
    "processingmethod": "string",
    "subprogram": "string",
    "initialinterestrate": "float",
    "naicscode": "string",
    "naicsdescription": "string",
    "franchisecode": "string",
    "franchisename": "string",
    "projectcounty": "string",
    "projectstate": "string",
    "sbadistrictoffice": "string",
    "congressionaldistrict": "string",
    "businesstype": "string",
    "businessage": "string",
    "loanstatus": "string",
    "paidinfulldate": "date",
    "chargeoffdate": "date",
    "grosschargeoffamount": "float",
    "fixedorvariableinterestind": "string",
    "terminmonths": "integer",
    "revolverstatus": "integer",
    "collateralind": "string",
    "soldsecmrktind": "string",
    "jobssupported":"integer",
}


STRING_COLUMNS = tuple(column for column, column_type in COLUMN_TYPES.items() if column_type == "string")
INTEGER_COLUMNS = tuple(column for column, column_type in COLUMN_TYPES.items() if column_type == "integer")
FLOAT_COLUMNS = tuple(column for column, column_type in COLUMN_TYPES.items() if column_type == "float")
DATE_COLUMNS = tuple(column for column, column_type in COLUMN_TYPES.items() if column_type == "date")






PROGRAM_VALUES = ("7a",)

LOAN_STATUS_VALUES = (
    "pif",
    "cancld",
    "curr",
    "chgoff",
    "purch(not c/o)",
    "clsln",
    "liquid",
    "delinq",
    "pstdue",
    "deferd",
    "commit",
    "soldnc",
)

REVOLVER_STATUS_VALUES = (0, 1)

INTEREST_IND_VALUES = ("f", "v")

BUSINESS_TYPE_VALUES = ("individual", "partnership", "corporation")

COLLATERAL_IND_VALUES = ("true", "false")

SOLD_SEC_MRKT_VALUES = ("y",)

BUSINESS_AGE_VALUES = (
    "change of ownership",
    "existing or more than 2 years old",
    "new business or 2 years or less",
    "startup, loan funds will open business",
)

PROCESSING_METHOD_VALUES = (
    "7a general",
    "7a with ewcp",
    "7a with wcp",
    "builders line of credit (capline)",
    "certified lenders program",
    "certified lenders program with ewcp",
    "community advantage initiative",
    "community advantage international trade",
    "community advantage rloc",
    "community advantage recovery loan",
    "community express",
    "contract loan line of credit (capline)",
    "dealer floor plan loans",
    "domestic revolving line of credit",
    "export express",
    "export import harmonization (exim)",
    "gulf opportunity pilot loan program",
    "international trade loans",
    "low documentation program",
    "patriot express loans",
    "preferred lenders program",
    "preferred lenders with ewcp",
    "preferred lenders with wcp",
    "rural loan initiative",
    "sba express bridge loan",
    "sba express program",
    "seasonal line of credit (capline)",
    "small asset base line of credit (capline)",
    "small loan advantage initiative",
    "standard asset base working capital line of credit (capline)",
)