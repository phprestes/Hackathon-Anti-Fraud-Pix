from errors import QIException


class NotFoundPixTransaction(QIException):
    code = "QIT002001"

    def __init__(self, pix_id) -> None:
        title = "Pix Transaction not Found"
        http_status = 404
        description = f"Pix transaction with id {pix_id} was not found."
        translation = f"A transação Pix com id {pix_id} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class PixIdConflict(QIException):
    code = "QIT002002"

    def __init__(self, pix_id) -> None:
        title = "Pix id already used with a different body"
        http_status = 409
        description = f"Pix transaction {pix_id} was already analyzed with a different body."
        translation = f"O Pix {pix_id} já foi analisado com um corpo diferente."
        super().__init__(title, self.code, http_status, description, translation)
