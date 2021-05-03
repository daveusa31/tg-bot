import re
import peewee
import typing
import ipaddress
import collections

try:
    import ujson as json
except ImportError:
    import json

from tg_bot.etc.database import exceptions


class Field(peewee.Field):
    def __init__(self, validators: typing.Union = (typing.AnyStr, typing.Callable), *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.validators: typing.Tuple = validators

    def db_value(self, value):
        if self.run_validators(value) is False:
            raise exceptions.ValidationError("The value({}) failed validation".format(value))

        return value

    def run_validators(self, value):
        for validator in self.validators:
            if isinstance(validator, str):
                result = value == validator
            else:  # Validator function
                result = validator(value)

            if result:
                break
        else:
            result = False

        return result


class CharField(peewee.CharField, Field):
    pass


class SmallIntegerField(peewee.SmallIntegerField, Field):
    pass


class BooleanField(peewee.BooleanField, Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_true(self, is_true=True):
        op = peewee.OP.EQ if is_true else peewee.OP.NE
        return peewee.Expression(self, op, 1)

    def is_false(self, is_false=True):
        op = peewee.OP.EQ if is_false else peewee.OP.NE
        return peewee.Expression(self, op, 0)


class BaseRegexField(CharField):
    regex = None
    min_length = 1
    max_length = 255

    def db_value(self, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()

            if value == "":
                RuntimeWarning(
                    f"{self.__class__.__name__}: Value is an Empty string!.")

            if len(value) > self.max_length:
                raise ValueError((
                    f"{self.__class__.__name__}: Value string is too long!. "
                    f"(valid values must be < {self.max_length} Characters):"
                    f" {len(value)} > {self.max_length} Characters, {value}."
                ))

            if len(value) < self.min_length:
                raise ValueError((
                    f"{self.__class__.__name__}: Value string is too short!. "
                    f"(valid values must be > {self.min_length} Characters):"
                    f" {len(value)} < {self.min_length} Characters, {value}."
                ))

            if not re.match(self.regex, value):
                raise ValueError((
                    f"{self.__class__.__name__}: Value string is not valid!. "
                    f"(valid values must match a Regex {self.regex}): {value}."
                ))

        return value


class SemVerField(BaseRegexField):
    """Semantic Versions Field (https://semver.org)."""
    regex = str(
        r"\bv?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[\d"
        r"a-z-]+(?:\.[\da-z-]+)*)?(?:\+[\da-z-]+(?:\.[\da-z-]+)*)?\b")


class ARZipCodeField(BaseRegexField):
    """Argentine Postal Codes Field (old & new)."""
    min_length = 4
    max_length = 8  # New = 8, Old = 4
    regex = r'^\d{4}$|^[A-HJ-NP-Za-hj-np-z]\d{4}\D{3}$'

    @staticmethod
    def get_html_widget(clas: tuple = None, ids: str = None,
                        required: bool = False) -> str:
        klas = f'''class="{' '.join(clas)}" ''' if clas else ""
        idz = f'id="{ids}" ' if ids else ""
        r = "required " if required else ""
        return str(f'<input type="text" name="postal-code" {idz}{klas}{r} '
                   'placeholder="Codigo Postal Argentino" '
                   'minlength="4" maxlength="8" size="8">\n')


class USZipCodeField(BaseRegexField):
    """US ZIP Codes Field (XXXXX or XXXXX-XXXX)."""
    min_length = 5
    max_length = 10
    regex = r'^\d{5}(?:-\d{4})?$'


class ATZipCodeField(BaseRegexField):
    """Austria ZIP Codes Field (4 digits)."""
    min_length = 4
    max_length = 4
    regex = r'^[1-9]{1}\d{3}$'


class AUZipCodeField(BaseRegexField):
    """Australia ZIP Codes Field (4 digits)."""
    min_length = 4
    max_length = 4
    regex = r'^\d{4}$'


class BEZipCodeField(BaseRegexField):
    """Belgium ZIP Codes Field (4 digits)."""
    min_length = 4
    max_length = 4
    regex = r'^[1-9]\d{3}$'


class BRZipCodeField(BaseRegexField):
    """Brazil ZIP Code Field (XXXXX-XXX format)."""
    min_length = 8
    max_length = 10
    regex = r'^\d{5}-\d{3}$'


class CHZipCodeField(BaseRegexField):
    """Swiss ZIP Code Field (4 digits)."""
    min_length = 4
    max_length = 4
    regex = r'^[1-9]\d{3}$'


class CLRutField(BaseRegexField):
    """Chile "Rol Unico Tributario" (RUT) Field.

    This is the Chilean national identification number. 'XX.XXX.XXX-X' format.
    More info: https://palena.sii.cl/cvc/dte/ee_empresas_emisoras.html."""
    max_length = 14
    regex = r'^(\d{1,2}\.)?\d{3}\.\d{3}-[\dkK]$'


class CNZipCodeField(BaseRegexField):
    """China ZIP Code (Mainland, 6 Digit) Field."""
    min_length = 6
    max_length = 6
    regex = r'^\d{6}$'


class CONITField(BaseRegexField):
    """Colombia NIT Field.

    Numero de IdentificaciOn Tributaria. NIT is of the form XXXXXXXXXX-V.
    The last digit is a check digit. NIT can be used for people and companies.

    http://es.wikipedia.org/wiki/N%C3%BAmero_de_Identificaci%C3%B3n_Tributaria.
    """
    min_length = 5
    max_length = 12
    regex = r'^\d{5,12}-?\d$'


class CUZipCodeField(BaseRegexField):
    """Cuba ZIP Codes (5 Digits) Field.

    http://mapanet.eu/Postal_Codes/?C=CU."""
    min_length = 5
    max_length = 6
    regex = r'^[1-9]\d{4}$'


class CZZipCodeField(BaseRegexField):
    """Czech ZIP Code Field (XXXXX or XXX XX)."""
    min_length = 5
    max_length = 6
    regex = r'^\d{5}$|^\d{3} \d{2}$'


class DEZipCodeField(BaseRegexField):
    """German ZIP Code Field (5 Digits)."""
    min_length = 5
    max_length = 5
    regex = r'^([0]{1}[1-9]{1}|[1-9]{1}[0-9]{1})[0-9]{3}$'


class EEZipCodeField(BaseRegexField):
    """Estonia ZIP Code Field (5 Digits)."""
    min_length = 5
    max_length = 5
    regex = r'^[1-9]\d{4}$'


class ESZipCodeField(BaseRegexField):
    """Spain ZIP Code Field (5 Digits).

    Spanish postal code is a five digits string,
    with two first digits between 01 and 52, assigned to provinces code."""
    min_length = 5
    max_length = 5
    regex = r'^(0[1-9]|[1-4][0-9]|5[0-2])\d{3}$'


class GRZipCodeField(BaseRegexField):
    """Greek ZIP Code Field (5 Digits)."""
    min_length = 5
    max_length = 5
    regex = r'^[12345678]\d{4}$'


class HROIBField(BaseRegexField):
    """Croatia Personal Identification Number Field, AKA OIB (11 Digits)."""
    min_length = 10
    max_length = 11
    regex = r'^\d{11}$'


class ILZipCodeField(BaseRegexField):
    """Israel ZIP Code Field."""
    min_length = 7
    max_length = 8
    regex = r'^\d{5}$|^\d{7}$'


class INZipCodeField(BaseRegexField):
    """India ZIP Code Field (XXXXXX or XXX XXX)."""
    min_length = 6
    max_length = 7
    regex = r'^\d{3}\s?\d{3}$'


class ISIdNumberField(BaseRegexField):
    """Iceland identification number Field, AKA Kennitala (XXXXXX-XXXX)."""
    min_length = 10
    max_length = 11
    regex = r'^\d{6}(-| )?\d{4}$'


class JPZipCodeField(BaseRegexField):
    """Japan ZIP Code Field."""
    max_length = 8
    regex = r'^\d{3}-\d{4}$|^\d{7}$'


class MKIdentityCardNumberField(BaseRegexField):
    """Macedonia ID card number Field (old & new)."""
    min_length = 4
    max_length = 8
    regex = r'(^[A-Z]{1}\d{7}$)|(^\d{4,7}$)'


class MTZipCodeField(BaseRegexField):
    """Maltese ZIP Code Field (7 digits, first 3 letters, final 4 numbers)."""
    min_length = 7
    max_length = 8
    regex = r'^[A-Z]{3}\ \d{4}$'


class MXZipCodeField(BaseRegexField):
    """Mexico ZIP Code Field (XXXXX format).

    http://en.wikipedia.org/wiki/List_of_postal_codes_in_Mexico."""
    min_length = 5
    max_length = 6
    regex = r'^(0[1-9]|[1][0-6]|[2-9]\d)(\d{3})$'


class PLNationalIDCardNumberField(BaseRegexField):
    """Polish National ID Card Number Field (3 letter and 6 digits).

    http://en.wikipedia.org/wiki/Polish_identity_card."""
    min_length = 9
    max_length = 10
    regex = r'^[A-Za-z]{3}\d{6}$'


class PLNIPField(BaseRegexField):
    """Polish Tax Number Field (NIP).

    The format is XXX-YYY-YY-YY, XXX-YY-YY-YYY or XXXYYYYYYY.
    http://wipos.p.lodz.pl/zylla/ut/nip-rego.html."""
    min_length = 10
    max_length = 15
    regex = r'^\d{3}-\d{3}-\d{2}-\d{2}$|^\d{3}-\d{2}-\d{2}-\d{3}$|^\d{10}$'


class PLZipCodeField(BaseRegexField):
    """Polish ZIP Code Field (XX-XXX format)."""
    min_length = 5
    max_length = 6
    regex = r'^\d{2}-\d{3}$'


class PTZipCodeField(BaseRegexField):
    """Portuguese ZIP Code Field.

    XYYY-YYY (where X is a digit between 1 and 9, Y is any other digit)."""
    min_length = 7
    max_length = 8
    regex = r'^[1-9]\d{3}-\d{3}$'


class ROZipCodeField(BaseRegexField):
    """Romania ZIP Code Field (XXXXXX format)."""
    min_length = 6
    max_length = 6
    regex = r'^[0-9][0-8][0-9]{4}$'


class ROCIFField(BaseRegexField):
    """Romania Fiscal Identity Code (CIF).

    https://ro.wikipedia.org/wiki/Cod_de_Identificare_Fiscal%C4%83."""
    min_length = 2
    max_length = 10
    regex = r'^(RO)?[0-9]{2,10}'


class ROCNPField(BaseRegexField):
    """Romania Personal Identity Code Field (CNP)."""
    min_length = 12
    max_length = 13
    regex = r'^[1-9][0-9]{12}'


class RUPassportNumberField(BaseRegexField):
    """Russian Passport Number Field (Internal or Alien).

    XXXX XXXXXX or XX XXXXXXX, where X is any digit."""
    max_length = 12
    regex = r'^\d{4} \d{6}$|^\d{2} \d{7}$'


class SEZipCodeField(BaseRegexField):
    """Swedish ZIP Code Field (5 digits).

    Can optionally be formatted with a space after the third digit (XXX XX)."""
    min_length = 5
    max_length = 6
    regex = r'^[1-9]\d{2} ?\d{2}$'


class SKZipCodeField(BaseRegexField):
    """Slovak ZIP Code Field (XXXXX or XXX XX, where X is integer)."""
    min_length = 5
    max_length = 6
    regex = r'^\d{5}$|^\d{3} \d{2}$'


class UAZipCodeField(BaseRegexField):
    """Ukrainian ZIP Code Field (5 digits,first 2 numbers must not be '00')."""
    min_length = 5
    max_length = 5
    regex = r'^(?!00)\d{5}$'


class UYCIField(BaseRegexField):
    """Uruguay Cedula de Identidad (X.XXX.XXX-X or XXXXXXX-X or XXXXXXXX)."""
    min_length = 8
    max_length = 12
    regex = r'(?P<num>(\d{6,7}|(\d\.)?\d{3}\.\d{3}))-?(?P<val>\d)'


class SimplePasswordField(CharField):
    def __init__(self, salt, min_length=8, algorithm="sha512", iterations=100_000, dklen=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_length = int(min_length) if min_length else None
        self.algorithm = str(algorithm).lower().strip()
        self.salt = bytes(str(salt).strip(), "utf-8")
        self.iterations = int(iterations)
        self.dklen = dklen

    def db_value(self, value):
        """Convert the python value for storage in the database."""
        if value and isinstance(value, str):
            value = value.strip()

            if value and self.min_length and len(value) < self.min_length:
                raise ValueError(
                    (f"{self.__class__.__name__} Value string is too short"
                     f" (valid values must be string of {self.min_length} "
                     f"characters or more): {len(value)} length,{value}."))

            return binascii.hexlify(hashlib.pbkdf2_hmac(
                self.algorithm, bytes(value, "utf-8"), self.salt,
                self.iterations, self.dklen)).decode("utf-8")

    def check_password(self, password_hash: str, password_literal: str) -> bool:
        if isinstance(password_hash, str) and isinstance(password_literal, str):
            digest = str(binascii.hexlify(hashlib.pbkdf2_hmac(
                self.algorithm, bytes(password_literal.strip(), "utf-8"),
                self.salt, self.iterations, self.dklen)).decode("utf-8"))
            return bool(secrets.compare_digest(password_hash, digest))
        return False


class PositiveSmallIntegerField(SmallIntegerField):
    """SmallIntegerField clone but only accepts Positive values (>= 0)."""

    # https://www.postgresql.org/docs/current/static/datatype-numeric.html
    min = 0
    max = 32_767

    def db_value(self, value):
        if value and isinstance(value, int):
            if value < self.min or value > self.max:
                raise ValueError(f"""{self.__class__.__name__} Value is not a
                Positive Integer (valid values must be Positive Integers
                between {self.min} and {self.max}): {value}.""")
        return value


class PositiveIntegerField(peewee.IntegerField, Field):
    """IntegerField clone but only accepts Positive values (>= 0)."""

    # https://www.postgresql.org/docs/current/static/datatype-numeric.html
    min = 0
    max = 2_147_483_647

    def db_value(self, value):
        if value and isinstance(value, int):
            if value < self.min or value > self.max:
                raise ValueError(f"""{self.__class__.__name__} Value is not a
                Positive Integer (valid values must be Positive Integers
                between {self.min} and {self.max}): {value}.""")
        return value


class PositiveBigIntegerField(peewee.BigIntegerField, Field):
    """BigIntegerField clone but only accepts Positive values (>= 0)."""

    # https://www.postgresql.org/docs/current/static/datatype-numeric.html
    min = 0
    max = 9_223_372_036_854_775_807

    def db_value(self, value):
        if value and isinstance(value, int):
            if value < self.min or value > self.max:
                raise ValueError(f"""{self.__class__.__name__} Value is not a
                Positive Integer (valid values must be Positive Integers
                between {self.min} and {self.max}): {value}.""")
        return value


class PositiveFloatField(peewee.FloatField, Field):
    """FloatField clone but only accepts Positive values (>= 0).

    Optionally it can round Floats using Pythons round() with round_by arg."""

    def __init__(self, round_by: int = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(round_by, int) and round_by <= 0:  # round_by is 0.
            raise ValueError(f"""{self.__class__.__name__} 'round_by' argument
            is not a Non-Zero Positive Integer number
            (valid values must be Integers > 0): {round_by}.""")
        if round_by and isinstance(round_by, int) and round_by > 0:
            self.round_by = int(round_by)
        else:
            self.round_by = None

    def db_value(self, value):
        if value and value < 0:
            raise ValueError(f"""{self.__class__.__name__} Value is not a
            Positive Float (valid values must be Floats >=0): {value}.""")

        if value and self.round_by:
            value = round(value, self.round_by)

        return value


class PositiveDecimalField(peewee.DecimalField, Field):
    """DecimalField clone but only accepts Positive values (>= 0).

    Optionally it can round Decimal using Decimal().quantize().normalize()."""

    def __init__(self, round_by: int = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(round_by, int) and round_by <= 0:  # round_by is 0.
            raise ValueError(f"""{self.__class__.__name__} 'round_by' argument
            is not a Non-Zero Positive Integer numbers
            (valid values must be Integers > 0): {round_by}.""")
        if round_by and isinstance(round_by, int) and round_by > 0:
            self.round_by = int(round_by)
        else:
            self.round_by = None

    def db_value(self, value):

        if value and value < 0:
            raise ValueError(f"""{self.__class__.__name__} Value is not a
            Positive Decimal (valid values must be Decimals >=0): {value}.""")

        if value and self.round_by:
            value = Decimal(value).quantize(
                Decimal(10) ** -self.round_by).normalize()

        return value


class HexadecimalField(peewee.BlobField, Field):
    """Hexadecimal String Field,stores arbitrary Hexadecimal as Binary.

    Useful for Promo Codes, Redeem Codes, Invitation Codes, etc etc."""
    regex = r"^(([0-9A-f])|(0x[0-9A-f]))+$"

    def db_value(self, value):
        if value and isinstance(value, str):
            if not re.match(self.regex, value):
                raise ValueError((
                    f"{self.__class__.__name__}: Value is not Hexadecimal. "
                    f"(valid values must match a Regex {self.regex}): {value}."
                ))
            return binascii.unhexlify(value)
        return value

    def python_value(self, value):
        if value:
            return binascii.hexlify(value).decode(encoding='UTF-8')
        return value


class SmallHexadecimalField(SmallIntegerField):
    """Small Hexadecimal str,stores arbitrary Hexadecimal as integer (Base 16).

    Useful for Promo Codes, Redeem Codes, Invitation Codes, etc etc.
    Converts the Hexadecimal String to Integer of Base16,
    stores only integers on the database, uses SmallIntegerField.

    For Big Long Hexadecimal strings use HexadecimalField (CharField based)."""
    regex = r"^(([0-9A-f])|(0x[0-9A-f]))+$"
    # https://www.postgresql.org/docs/current/static/datatype-numeric.html
    min = 0
    max = 32_767

    def db_value(self, value):
        if value and isinstance(value, str):
            if value == "":
                raise ValueError(
                    f"{self.__class__.__name__}: Value is an Empty string!.")

            if not re.match(self.regex, value):
                raise ValueError((
                    f"{self.__class__.__name__}: Value string is not valid!. "
                    f"(valid values must match a Regex {self.regex}): {value}."
                ))

            value = int(value.lower().strip(), 16)  # string to integer.

            if value < self.min or value > self.max:
                raise ValueError((
                    f"{self.__class__.__name__} Value is too Big or too Small!, "
                    f"(valid values must be between {self.min} and {self.max}, "
                    f"the Field internally uses a {SmallIntegerField}): {value}."))
        return value

    def python_value(self, value):
        if value and isinstance(value, int):
            value = hex(value & 0xffffffff)[2:]
        return value


class IPAddressField(peewee.BigIntegerField, Field):
    """BigIntegerField clone but only accepts IP Address, returns ip_address.

    This works transparently with IPv4 and IPv6 Addresses.
    Inspired by:
    docs.djangoproject.com/en/1.11/ref/models/fields/#genericipaddressfield and
    https://devdocs.io/python~3.6/library/ipaddress."""

    def db_value(self, value: str):
        if value and isinstance(value, (str, int)):
            try:
                ipaddress.ip_address(value)
            except Exception as error:
                raise ValueError(f"""{self.__class__.__name__} IP Value is
                not a Valid IP v4 or v6 Address (valid values must be a valid
                {ipaddress.ip_address} {ipaddress.IPv4Address}): {value} --> {error}.""")
            else:
                return int(ipaddress.ip_address(value))  # Valid IPv4Address/IPv6Address.
        return value  # is None.

    def python_value(self, value: str) -> ipaddress.IPv4Address:
        return ipaddress.ip_address(value) if value else value


class IPNetworkField(CharField):
    """CharField clone but only accepts IP Network values, returns ip_network.

    This works transparently with IPv4 and IPv6 Networks.
    Inspired by:
    docs.djangoproject.com/en/1.11/ref/models/fields/#genericipaddressfield and
    https://devdocs.io/python~3.6/library/ipaddress."""

    def db_value(self, value: str) -> str:
        if value and isinstance(value, str):
            try:
                ipaddress.ip_network(value)
            except Exception as error:
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid IP v4 or v6 Network (valid values must be a valid
                {ipaddress.ip_network} {ipaddress.IPv4Network}): {value} --> {error}.""")
            else:
                return value  # is a valid IPv4Network or IPv6Network.
        return value  # is None.

    def python_value(self, value: str) -> ipaddress.IPv4Network:


class SWIFTISOCodeField(CharField):
    """CharField clone but only accepts SWIFT-Codes ISO-9362 values.

    CharField for SWIFT Business Identifier Code (BIC ISO-9362:2014, AKA SWIFT)
    https://en.wikipedia.org/wiki/ISO_9362."""
    max_length = 11

    def db_value(self, value: str) -> str:
        if isinstance(value, str):
            value = value.strip().replace(' ', '').replace('-', '').upper()

            if len(value) == 12:  # Must be ISO-9362:2014.
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid SWIFT-Code ISO-9362:2014
                (12-Character SWIFTNet FIN Address based on BIC is not Valid,
                Internal 'BIC12' are not part of the ISO Standard): {value}""")

            if value == "":
                raise ValueError(f"""{self.__class__.__name__}
                Value string is not a Valid SWIFT-Code ISO-9362:2014
                (valid values must not be an Empty String): {value}.""")

            if not (len(value) == 8 or len(value) == 11):
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid SWIFT-Code ISO-9362:2014 (valid values must be a
                valid SWIFT-Code of 8 or 11 characters long): {value}.""")

            bank_code = value[:4]  # First 4 letters must be A ~ Z.
            for x in bank_code:
                if x not in string.ascii_uppercase:
                    raise ValueError(f"""{self.__class__.__name__} Value string
                    is not a Valid SWIFT-Code ISO-9362:2014 (valid values must
                    be a valid SWIFT-Code, the first 4 Letters must be A-Z):
                    {value} -> {x}.""")

            country_code = value[4:6].lower()  # Letters 5 & 6 is ISO 3166-1.
            if country_code not in ISO3166:
                raise ValueError(f"""{self.__class__.__name__} Value string
                is not a Valid SWIFT-Code ISO-9362:2014 (valid values must
                be a valid SWIFT-Code, the letters 5 and 6 must consist of an
                ISO-3166-1 Alpha-2 Country Code): {value} -> {country_code}""")

        return value

    def python_value(self, value: str) -> collections.namedtuple:
        if value and isinstance(value, str):
            branch_code = value[8:11] if value[8:11] != "" else None
            return collections.namedtuple(
                "SWIFTCodeISO9362",
                "bank_code country_code location_code branch_code swift")(
                value[:4], value[4:6], value[6:8], branch_code, value)
        return value


class IBANISOCodeField(CharField):
    """CharField clone but only accepts IBAN-Codes ISO 13616 values.

    CharField for International Bank Account Number IBAN Code (ISO-13616:2007).
    https://en.wikipedia.org/wiki/International_Bank_Account_Number.
    wikipedia.org/wiki/International_Bank_Account_Number#Validating_the_IBAN."""
    max_length = 34

    def db_value(self, value: str) -> str:
        if isinstance(value, str):
            value = value.strip().replace(' ', '').replace('-', '').upper()

            if value == "":
                raise ValueError(f"""{self.__class__.__name__}
                Value string is not a Valid IBAN-Code ISO-13616:2007
                (valid values must not be an Empty String): {value}.""")

            if len(value) > 34:
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid IBAN-Code ISO-13616:2007 (valid values must be a
                valid IBAN-Code ISO-13616 of 34 characters max): {value}.""")

            country_code = value[:2].lower()
            if country_code not in ISO3166:
                raise ValueError(f"""{self.__class__.__name__} Value string
                is not a Valid IBAN-Code ISO-13616:2007 (valid values must be a
                valid IBAN-Code, must contain a ISO-3166 Alpha-2 Country Code):
                {value} -> {country_code}.""")

            iban_checksum = value[2:4].lower()
            if not iban_checksum.isdigit():
                raise ValueError(f"""{self.__class__.__name__} Value string
                is not a Valid IBAN-Code ISO-13616:2007 (valid values must be a
                valid IBAN-Code, must contain a Valid IBAN CheckSum Digit):
                {value} -> {iban_checksum}.""")

            if self.get_iban_checksum(value) != value[2:4]:
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid IBAN-Code ISO-13616:2007 (valid values must have a
                valid IBAN CheckSum digits): {value} -> {value[2:4]}.""")

        return value

    def python_value(self, value: str) -> collections.namedtuple:
        if value and isinstance(value, str):
            value = value.strip().replace(' ', '').replace('-', '').upper()
            # Pretty format for IBAN has 1 white space every 4 characters.
            pretty = ' '.join(value[i:i + 4] for i in range(0, len(value), 4))
            return collections.namedtuple(
                "SWIFTCodeISO9362",
                "country_code checksum bban iban_pretty iban")(
                value[:2], value[2:4], value[4:], pretty, value)
        return value

    @staticmethod
    def get_iban_checksum(value: str) -> str:
        """Return check digits for an input IBAN number,original is ignored."""
        value = value.strip().replace(' ', '').replace('-', '').upper()
        value = value[4:] + value[:2] + '00'
        value_digits = ''
        for x in value:
            if '0' <= x <= '9':
                value_digits += x
            elif 'A' <= x <= 'Z':
                value_digits += str(ord(x) - 55)
            else:
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid IBAN-Code ISO-13616:2007 (valid values must have a
                valid IBAN CheckSum integer number): {value} -> {x}.""")
        return '%02d' % (98 - int(value_digits) % 97)
        return ipaddress.ip_network(value) if value else value


class IANCodeField(CharField):
    """CharField clone but only accepts IAN-Codes values.

    CharField for International Article Number (AKA European Article Number).
    Notice this is not an ISO Standard. CheckSum for 8 to 13 IAN-Codes only.
    https://en.wikipedia.org/wiki/International_Article_Number (EAN)."""
    max_length = 13

    def db_value(self, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()

            if value == "":
                raise ValueError(f"""{self.__class__.__name__}
                Value string is not a Valid International Article Number (IAN)
                (valid values must not be an Empty String): {value}.""")

            if len(value) > 13:
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid International Article Number (IAN) (valid values
                must be a valid IAN of 13 characters max): {value}.""")

            if len(value) > 7 and self.get_ian_checksum(value) != value[-1]:
                raise ValueError(f"""{self.__class__.__name__} Value string is
                not a Valid International Article Number IAN 8~13 Characters
                (valid values must have a valid IAN CheckSum int): {value}.""")

        return value

    @staticmethod
    def get_ian_checksum(value: str):
        """Return checksum for IAN, original is ignored."""
        try:
            calculated_checksum = sum(
                int(digit) * (3, 1)[i % 2]
                for i, digit in enumerate(reversed(value[:-1])))
            calculated_checksum = str(10 - (calculated_checksum % 10))
            return calculated_checksum
        except ValueError as error:  # Raised if an int conversion fails
            return error


class PastDateTimeField(peewee.DateTimeField):
    """DateTimeField clone but dont allow Dates and Times on the Future.

    Past is Ok, Present is Ok, Future is Not Ok.
    Most of times you need DateTimes on Past,eg. Bday cant be in the Future."""

    def db_value(self, value):
        # developer.mozilla.org/en/docs/Web/HTML/Element/input/datetime-local
        if value and isinstance(value, str):
            # http:docs.peewee-orm.com/en/latest/peewee/api.html#DateTimeField
            for datetime_format in self.formats:
                try:
                    valid_datetime = datetime.strptime(value, datetime_format)
                except Exception:
                    pass  # this datetime_format does not match value.
                else:
                    break  # this datetime_format match value.
            if valid_datetime.today() > date.today():
                raise ValueError(f"""{self.__class__.__name__} Dates & Times
                Value is not in the Past (valid values must be in the Past):
                {valid_datetime}, {value} > {datetime.utcnow().isoformat()}""")
        if value and isinstance(value, datetime):
            if value > datetime.utcnow():
                raise ValueError(f"""{self.__class__.__name__} Dates & Times
                Value is not in the Past (valid values must be in the Past):
                {value} > {datetime.utcnow().isoformat()}.""")
        return value

    @staticmethod
    def get_html_widget(clas: tuple = None, ids: str = None,
                        required: bool = False) -> str:
        clas = f'''class="{' '.join(clas)}" ''' if clas else ""
        ids = f'id="{ids}" ' if ids else ""
        r = "required " if required else ""
        return (f'<input type="datetime-local" name="datetime" {ids}{clas}{r}'
                f'''max="{datetime.utcnow().strftime('%Y-%m-%dT%H:%M')}">\n''')


class PastDateField(peewee.DateField, Field):
    """DateField clone but dont allow Dates on the Future.

    Past is Ok, Present is Ok, Future is Not Ok.
    Most of times you need Dates on the Past,eg. Bday cant be in the Future."""

    def db_value(self, value):  # check if its valid for date()
        if value and isinstance(value, str):
            # http:developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date
            for date_format in self.formats:
                try:  # docs.peewee-orm.com/en/latest/peewee/api.html#DateField
                    valid_date = datetime.strptime(value, date_format).date()
                except Exception:
                    pass  # this date_format does not match value.
                else:
                    break  # this date_format match value.
            if valid_date > date.today():
                raise ValueError(f"""{self.__class__.__name__} Dates Value is
                not in the Past (valid values must be in the Past or Present):
                {valid_date}, {value} > {datetime.date.today()}.""")
        if value and isinstance(value, datetime.date):
            if value > datetime.date.today():
                raise ValueError(f"""{self.__class__.__name__} Dates Value is
                not in the Past (valid values must be in the Past or Present):
                {value} > {datetime.date.today()}.""")
        return value

    @staticmethod
    def get_html_widget(clas: tuple = None, ids: str = None,
                        required: bool = False) -> str:
        clas = f'''class="{' '.join(clas)}" ''' if clas else ""
        ids = f'id="{ids}" ' if ids else ""
        r = "required " if required else ""
        return (f'<input type="date" name="date" {ids}{clas}{r} '


class LanguageISOCodeField(peewee.FixedCharField, Field):
    """FixedCharField clone only accepts Language ISO Code values.

    Returns 1 namedtuple with 2-chars code str and human-friendly name str.
    I cant find an ISO-Numeric standard mapping to optimize this to SmallInt."""
    max_length = 2

    def db_value(self, value: str) -> str:
        if value and isinstance(value, str):
            value = value.lower().strip()

            if len(value) != 2:
                raise ValueError(f"""{self.__class__.__name__} Value is
                {len(value)} Characters long instead of 2 Characters long
                (valid values must be ISO-639_1 Language Codes): {value}.""")

            if len(value) == 2 and value not in ISO639_1:
                raise ValueError(f"""{self.__class__.__name__} Value is not an
                ISO-639_1 Standard Language Code of 2 Characters long
                (valid values must be ISO-639_1 Language Codes): {value}.""")

        return value

    def python_value(self, value: str) -> collections.namedtuple:
        if value and isinstance(value, str):
            lang = ISO639_1.get(value).get  # OPTIMIZATION
            return collections.namedtuple("LanguageISO639", "code name name_native")(
                value, lang("name").title(), lang("name_native").title())

        return value

    @staticmethod
    def get_html_widget(clas: tuple = None, ids: str = None,
                        required: bool = False) -> str:
        clas = f'''class="{' '.join(clas)}" ''' if clas else ""
        ids = f'id="{ids}" ' if ids else ""

        r = 'required="required" ' if required else ""
        html_widget = (f'<select name="language" {ids}{clas}{r}>\n'
                       '    <option selected disabled value=""></option>\n')

        for lang in ISO639_1.items():
            html_widget += (
                f'    <option value="{lang[0]}">({lang[0].upper()}) '
                f'{lang[1]["name"].title()} ({lang[1]["name_native"]})'
                '</option>\n')
        else:
            html_widget += '</select>\n'
            return html_widget


class CountryISOCodeField(SmallIntegerField):
    """SmallIntegerField clone only accepts Country ISO Code string values.

    It converts the 2-Characters Country ISO Code to integer Country ISO Code,
    saves to Database the SmallInt, when reading from Database, reverts back,
    small integer Country ISO Code to 2-Characters string Country ISO Code.

    Returns 1 namedtuple with iso3166_a3, iso3166_numeric, capital, continent,
    currency_code, currency_name, geoname_id, is_developed, is_independent,
    languages, name, name_human, phone_code, timezones and tld.

    This always stores only small positive Integer numbers of 3 digits max,
    that maps 1-to-1 to 2-Characters string Country Codes, according to ISO.

    Small integer is always faster than varchar or text in every aspect.
    """

    def db_value(self, value: str) -> int:
        if value and isinstance(value, str):
            value = value.lower().strip()

            if len(value) != 2:
                raise ValueError(f"""{self.__class__.__name__} Value is
                {len(value)} Characters long instead of 2 Characters long
                (valid values must be ISO-3166 Country Codes): {value}.""")

            if len(value) == 2 and value not in ISO3166:
                raise ValueError(f"""{self.__class__.__name__} Value is not an
                ISO-3166 Standard Country Code of 2 Characters long
                (valid values must be ISO-3166 Country Codes): {value}.""")

            if len(value) == 2 and value in ISO3166:  # str -> int.
                value = int(ISO3166.get(value).get("iso3166_numeric"))

        return value

    def python_value(self, value: int) -> collections.namedtuple:
        if value and isinstance(value, int):
            value = INT2COUNTRY[str(value)]  # int -> str.
            country = ISO3166[value].get  # OPTIMIZATION

            return collections.namedtuple(
                "CountryISO3166",
                ("iso3166_a3 iso3166_numeric capital continent currency_code "
                 "currency_name geoname_id is_developed is_independent "
                 "languages name name_human phone_code timezones tld")
            )(
                country("iso3166_a3").upper(),
                country("iso3166_numeric"),
                country("capital").title(),
                country("continent").title(),
                country("currency_code").upper(),
                country("currency_name").title(),
                country("geoname_id"),
                country("is_developed"),
                country("is_independent"),
                country("languages"),
                country("name").title(),
                country("name_human").title(),
                country("phone_code"),
                country("timezones"),
                country("tld"),
            )

        return value

    @staticmethod
    def get_html_widget(clas: tuple = None, ids: str = None,
                        required: bool = False) -> str:
        clas = f'''class="{' '.join(clas)}" ''' if clas else ""
        ids = f'id="{ids}" ' if ids else ""

        r = 'required="required" ' if required else ""
        html_widget = (f'<select name="country" {ids}{clas}{r}>\n'
                       '    <option selected disabled value=""></option>\n')

        for c in ISO3166.items():
            html_widget += (
                f'    <option value="{c[0]}" data-iso3166numeric="'
                f'''{str(str(c[1]["iso3166_numeric"]) + '"').ljust(4)} '''
                f'data-iso3166a3="{c[1]["iso3166_a3"]}">({c[0].upper()}) '
                f'{c[1]["name"].title()}</option>\n')
        else:
            html_widget += '</select>\n'
            return html_widget


class CurrencyISOCodeField(SmallIntegerField):
    """SmallIntegerField clone only accepts Currency ISO Code values.

    It converts 3-Characters Currency ISO Code to integer Currency ISO Code,
    saves to Database the SmallInt, when reading from Database, reverts back,
    small integer Currency ISO Code to 3-Characters string Currency ISO Code.

    Returns 1 namedtuple with code, name, iso4217_numeric.

    This always stores only small positive Integer numbers of 3 digits max,
    that maps 1-to-1 to 3-Characters string Currency Codes, according to ISO.

    Small integer is always faster than varchar or text in every aspect.
    """

    def db_value(self, value: str) -> int:
        if value and isinstance(value, str):
            value = value.lower().strip()

            if len(value) != 3:
                raise ValueError(f"""{self.__class__.__name__} Value is
                {len(value)} Characters long instead of 3 Characters long
                (valid values must be ISO-4217 Currency Codes): {value}.""")

            if len(value) == 3 and value not in ISO4217:
                raise ValueError(f"""{self.__class__.__name__} Value is not an
                ISO-4217 Standard Currency Code of 3 Characters long
                (valid values must be ISO-4217 Currency Codes): {value}.""")

            if len(value) == 3 and value in ISO4217:  # str -> int.
                value = int(ISO4217.get(value).get("iso4217_numeric"))

        return value

    def python_value(self, value: int) -> collections.namedtuple:
        if value and isinstance(value, int):
            value = INT2CURRENCY.get(str(value))  # int -> str.

            return collections.namedtuple("CurrencyISO4217", "code name iso4217_numeric")(
                value,
                ISO4217.get(value).get("name").title(),
                ISO4217.get(value).get("iso4217_numeric")
            )

        return value

    @staticmethod
    def get_html_widget(clas: tuple = None, ids: str = None,
                        required: bool = False) -> str:
        clas = f'''class="{' '.join(clas)}" ''' if clas else ""
        ids = f'id="{ids}" ' if ids else ""
        not_bill_money = ("che", "chw", "clf", "cou", "mxv", "usn", "uss",
                          "xag", "xau", "xba", "xbb", "xbc", "xbd", "xdr",
                          "xpd", "xpt", "xsu", "xts", "xua", "xxx", "uyi")

        r = 'required="required" ' if required else ""
        html_widget = (f'<select name="currency" {ids}{clas}{r}>\n'
                       '    <option selected disabled value=""></option>\n')

        for mon in ISO4217.items():
            if mon[0] not in not_bill_money:
                html_widget += (
                    f'    <option value="{mon[0]}" data-iso4217numeric="'
                    f'''{str(str(mon[1]["iso4217_numeric"]) + '"').ljust(4)}>'''
                    f'({mon[0].upper()}) {mon[1]["name"].title()}'
                    '</option>\n')
        else:
            html_widget += '</select>\n'
            return html_widget
                f'max="{datetime.date.today()}">\n')


class CharFieldCustom(CharField):
    """CharField clone but has additional options, min_len,blacklist,etc."""

    # TODO improve blacklist/whitelist matching somehow?, how?.  Better Name?.
    def __init__(self, min_lenght: int = None, use_lower: bool = False,
                 blacklist: tuple = None, whitelist: tuple = None,
                 force_ascii: str = None, force_slugify: bool = False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blacklist = tuple(sorted(set(blacklist))) if blacklist else None
        self.whitelist = tuple(sorted(set(whitelist))) if whitelist else None
        self.min_lenght = int(min_lenght) if min_lenght else None
        self.force_ascii = force_ascii
        self.force_slugify = force_slugify
        self.use_lower = use_lower

    def db_value(self, value):

        if value and self.use_lower:
            value = value.lower()

        if value and self.min_lenght and not len(value) >= self.min_lenght:
            raise ValueError(
                (f"{self} Value string is too short (valid values must be a "
                 f"string of {self.min_lenght} characters or more): {value}."))

        if value and self.blacklist and value.lower() in self.blacklist:
            raise ValueError(f"{self} Value string is black-listed: {value}.")

        if value and self.whitelist and value.lower() not in self.whitelist:
            raise ValueError((f"{self} Value string requires at least 1 "
                              "white-listed value present: {value}."))

        if value and self.force_ascii is not None:
            value = re.sub(r"[^\x00-\x7F]+", self.force_ascii,
                           value, flags=re.IGNORECASE)

        if value and self.force_slugify:
            value = re.sub(r'[^a-z0-9_\-]+', '-', value, flags=re.IGNORECASE)

        return value


class CSVField(CharField):
    """CharField clone but only accepts CSV string values (comma separated).

    Does not accepts CSV Headers. Has options for separator, set, sorted.
    Set and Sorted options may alter original order, use with caution.

    Inspired by CommaSeparatedIntegerField from Django."""

    # TODO Use other DB Type?, Array?, How?.
    def __init__(self, separator: str = ",", use_set: bool = False,
                 use_sorted: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.separator_character = str(separator)
        self.use_set = bool(use_set)
        self.use_sorted = bool(use_sorted)

    def db_value(self, value: str) -> str:
        if value and isinstance(value, str):
            value = value.split(self.separator_character)  # str -> list

            if self.use_set:  # list -> set
                value = set(value)  # Lost of Order!.

            if self.use_sorted:  # list -> list
                value = sorted(value)  # Lost of Order?.

            value = self.separator_character.join(value)
        return value

    def python_value(self, value: str) -> tuple:
        return tuple(value.split(self.separator_character) if value else [])


class ColorHexadecimalField(peewee.FixedCharField, Field):
    """FixedCharField clone only accepts Hexadecimal RGB Color values.

    3 Digit Hexadecimal colors are expanded by doubling each digit.
    6 Digit Hexadecimal colors are keep as-is untouched.
    Must start with a '#' as any Hexadecimal color.
    https://www.w3.org/TR/2001/WD-css3-color-20010305#colorunits
    https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/color."""
    max_length = 7

    def db_value(self, value: str) -> str:
        if isinstance(value, str):
            value = value.lower().replace("-", "").strip()

            if len(value) != 7 and len(value) != 4:
                raise ValueError(f"""{self.__class__.__name__} Value is
                {len(value)} Characters long instead of 7 or 4 Characters long
                (valid values must be exactly 7 or 4 characters): {value}.""")

            if not value.startswith("#"):
                raise ValueError(f"""{self.__class__.__name__} Value is not a
                valid RGB Hexadecimal Color value of 7 or 4 characters long
                (valid values must start with '#'): {value} -> {value[0]} .""")

            try:
                int(value[1:], 16)
            except ValueError as error:
                raise ValueError(f"""{self.__class__.__name__} Value is not an
                Hexadecimal (values must be Hexadecimals): {value} {error}""")

            if len(value) == 4:  # Short 3 char version to long 6 char version.
                value = f"#{value[1] * 2}{value[2] * 2}{value[3] * 2}"

        return value

    def python_value(self, value: str) -> collections.namedtuple:
        if value and isinstance(value, str):
            rgb = self.hex2rgb(value.replace("#", ""))
            hls = colorsys.rgb_to_hls(rgb.red, rgb.green, rgb.blue)
            hsv = colorsys.rgb_to_hsv(rgb.red, rgb.green, rgb.blue)
            yiq = colorsys.rgb_to_yiq(rgb.red, rgb.green, rgb.blue)

            hls = collections.namedtuple("HLS", "h l s")(  # Round,default precision huge
                round(hls[0], 2), round(hls[1], 2), round(hls[2], 2))
            hsv = collections.namedtuple("HSV", "h s v")(
                round(hsv[0], 2), round(hsv[1], 2), round(hsv[2], 2))
            yiq = collections.namedtuple("YIQ", "y i q")(
                round(yiq[0], 2), round(yiq[1], 2), round(yiq[2], 2))
            per = lambda val: int(val * 100 / 255)  # Percent, 0~255 > 0~100%

            return collections.namedtuple(
                "Color", "hex rgb hls hsv yiq css css_prcnt")(
                value, rgb, hls, hsv, yiq,
                f"rgb({rgb.red},{rgb.green},{rgb.blue})",  # rgb(int, int, int)
                f"rgb({per(rgb.red)}%,{per(rgb.green)}%,{per(rgb.blue)}%)")  # %

        return value

    @staticmethod
    def hex2rgb(color_hex: str) -> collections.namedtuple:
        return collections.namedtuple("RGB", "red green blue")(*struct.unpack(
            'BBB', codecs.decode(bytes(color_hex, "utf-8"), "hex")))


class EmailField(CharField):
    """A CharField that checks that the value is a valid Email address.

    max_length is Hardcoded to 254 to be compliant with RFCs 3696 and 5321.
    Max length for domain name is 63 Characters to be compliant with RFC-1034.

    str.lower() of the value string is Forced, to Normalize and simplify, KISS
    (RFC says uppercase & lowercase email addresses are 2 different addresses).
    https://code.djangoproject.com/ticket/17561#comment:7.

    Gravatar capability is provided using method email2gravatar(email)."""
    max_length = 254

    user_regex = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*\Z"
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"\Z)',
        re.IGNORECASE)
    domain_regex = re.compile(
        r'((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+)(?:[A-Z0-9-]{2,63}(?<!-))\Z',
        re.IGNORECASE)

    def db_value(self, value: str) -> str:
        if isinstance(value, str):
            value = value.strip().lower()

            if value == "":
                raise ValueError(
                    f"{self.__class__.__name__}: Value is an Empty string!.")

            if len(value) > self.max_length:
                raise ValueError((
                    f"{self.__class__.__name__}: Value string is too long!. "
                    f"(valid values must be < {self.max_length} Characters, "
                    "to be compliant with RFC-3696 and RFC-5321): "
                    f"{len(value)} > {self.max_length} Characters, {value}."
                ))

            if len(value) < 4:
                raise ValueError((
                    f"{self.__class__.__name__}: Value string is too short!. "
                    f"(valid values must be > 3 Characters): {value}."
                ))

            if "@" not in value:
                raise ValueError((
                    f"{self.__class__.__name__}: Value is not a Valid Email!. "
                    f"(valid values must have an '@' Character): {value}."
                ))

            user_part, domain_part = value.rsplit('@', 1)

            if len(domain_part) > 63:
                raise ValueError((
                    f"{self.__class__.__name__}: Value is not a Valid Email!. "
                    "Max length for domain name is 63 Characters per RFC-1034 "
                    f"(valid value domain name must be < 63 Characters long): "
                    f"{len(value)} > 63 Characters long, {value}."
                ))

            if not self.user_regex.match(user_part):
                raise ValueError((
                    f"{self.__class__.__name__}: Value is not a Valid Email!. "
                    f"(valid values must match a Regex {self.user_regex}): "
                    f"The username part {user_part} is invalid, {value}."
                ))

            is_localhost = domain_part == "localhost"  # Domain is localhost.
            try:
                ip_address(domain_part)  # Domain is literal IP.
                is_ipaddress = True
            except Exception:
                is_ipaddress = False

            if (not self.domain_regex.match(domain_part) and
                    not is_localhost and not is_ipaddress):
                raise ValueError((
                    f"{self.__class__.__name__}: Value is not a Valid Email!. "
                    f"(valid values must match a Regex {self.domain_regex}): "
                    f"The domain part {domain_part} is invalid, {value}."
                ))

        return value

    @staticmethod
    def email2gravatar(email, size: int = 512, rating: str = "r") -> str:
        _url = 'https://secure.gravatar.com/'  # 'http://www.gravatar.com/'
        _hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
        default = choice(('mm', 'identicon', 'monsterid', 'wavatar', 'retro'))
        query_str = urlencode({'s': str(int(size)), 'd': default, 'r': rating})
        return f'{_url}avatar/{_hash}.jpg?{query_str}'


class EnumField(SmallIntegerField):
    """This class enables a Enum like field for Peewee."""

    def __init__(self, enum, *args, **kwargs):
        if not issubclass(enum, Enum):
            raise TypeError((f"{self.__class__.__name__} Argument enum must be"
                             f" subclass of enum.Enum: {enum} {type(enum)}."))
        self.enum = enum
        super().__init__(*args, **kwargs)

    def db_value(self, member):
        return member.value

    def get_enum(self):
        return self.enum

    def python_value(self, value):
        enum = self.get_enum()
        return enum(value)

    def coerce(self, value):
        enum = self.get_enum()
        if value not in enum:
            raise ValueError((f"{self.__class__.__name__} the value must be "
                              f"member of the enum: {value}, {enum}."))


class MoneyField(Field):
    """Money Field, uses Native Monetary Database Type, accepts int,float,str.

    8 Bytes, from $ -92233720368547758.08 to $ +92233720368547758.07.
    https://www.postgresql.org/docs/current/static/datatype-money.html."""
    field_type = 'money'

    def db_value(self, value):
        if not isinstance(value, (int, float, str, Decimal, type(None))):
            raise TypeError((
                f"{self.__class__.__name__} Monetary value must be of Type "
                f"int, float, str, Decimal or None: {value}, {type(value)}."))
        return value


class XMLField(Field):
    """XML Field, uses Native XML Database Type, accepts str.

    Works with XML, SVG, XHTML, etc.
    https://www.postgresql.org/docs/current/static/datatype-xml.html."""
    field_type = 'xml'

    def db_value(self, value):
        if value and isinstance(value, str):
            value = value.strip()
            try:
                ET.fromstring(value)
            except Exception as error:
                raise ValueError((
                    f"{self.__class__.__name__} Value is not valid XML data. "
                    f"(valid values must be parseable by {ET}): {error}."))
        return value


class DateTimeTZRangeField(Field):
    """Date&Time Time Zone Field usin 'tstzrange' PostgreSQL type."""
    db_field = 'tstzrange'


# TODO: переписать. Посмотреть, как сделать у django
class FileField(CharField):
    """File field"""

    def __init__(self, folder_for_files="peewee_files\\", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder_for_files = folder_for_files
        if os.path.exists(self.folder_for_files) is False:
            os.mkdir(self.folder_for_files)

    def db_value(self, path_or_bytesio):
        if isinstance(path_or_bytesio, str):
            file_name = os.path.basename(path_or_bytesio)
            file_path = self.gen_path_for_file(file_name)
            shutil.copyfile(path_or_bytesio, file_path)

        elif isinstance(path_or_bytesio, io.IOBase):
            file_name = self.get_file_name(path_or_bytesio)
            file_path = self.gen_path_for_file(file_name)

            with open(file_path, "wb") as f:
                f.write(path_or_bytesio.read())

        else:
            file_path = None

        return file_path

    def python_value(self, value):
        if value is not None:
            file_path = value
            with open(value, "rb") as value:
                value.bytecode = value.read()

            value.file_path = file_path

        return value

    def gen_path_for_file(self, file_name, file_id=1):
        path = os.path.join(self.folder_for_files, file_name)
        if os.path.exists(path):
            file_name_without_extension_ = os.path.splitext(file_name)[0]
            file_extension = os.path.splitext(file_name)[1]
            _file_name = f"{file_name_without_extension_}_{file_id}{file_extension}"
            path = os.path.join(self.folder_for_files, _file_name)
            if os.path.exists(path):
                return self.gen_path_for_file(file_name, file_id=file_id + 1)

        return path

    @staticmethod
    def get_file_name(obj):
        """
        Get file name from object
        :param obj:
        :return: str
        """
        name = getattr(obj, 'name', None)
        if name and isinstance(name, str) and name[0] != "<" and name[-1] != ">":
            response = os.path.basename(name)
        else:
            response = None

        return response


class TextField(peewee.TextField, CharField):
    pass


class JSONField(TextField):
    """json field"""

    field_type = "json"

    def __init__(self, ensure_ascii=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ensure_ascii = ensure_ascii

    def db_value(self, value):
        if value is None:
            pass

        elif "" == value or 0 == len(value):
            value = "{}"

        elif isinstance(value, list) or isinstance(value, dict):
            ensure_ascii = self.ensure_ascii
            value = json.dumps(value, ensure_ascii=ensure_ascii)  # list -> str

        elif not self.is_json(value):
            raise ValueError

        return value

    def python_value(self, value):
        if value is not None:
            value = json.loads(value)
        return value

    @staticmethod
    def is_json(json_string):
        try:
            json.loads(json_string)
            response = True
        except TypeError:
            response = False

        return response

# Most Wanted Fields:
# - GeometryField
# - PointField
# - LineStringField
# - PolygonField
# - MultiPointField
# - MultiLineStringField
# - MultiPolygonField
# - GeometryCollectionField
# - RasterField
