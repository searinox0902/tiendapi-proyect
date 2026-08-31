---
updatedAt: 2026-05-26T23:02:12.000Z
---

Fetch the complete documentation index at: https://e-provider-docs.alegra.com/llms.txt. Use this file to discover all available pages before exploring further. Append .md to any documentation page URL to get its markdown version.

# Endpoint para dar de alta a una empresa

Este endpoint permite dar de alta empresas en la API con las configuraciones necesarias para enviar documentos a la DIAN

# OpenAPI definition

```json
{
  "openapi": "3.0.0",
  "info": {
    "version": "1",
    "title": "API Alegra Proveedor Electrónico Colombia",
    "license": {
      "name": "MIT"
    }
  },
  "servers": [
    {
      "url": "https://sandbox-api.alegra.com/e-provider/col/v1",
      "description": "Sandbox server"
    },
    {
      "url": "https://api.alegra.com/e-provider/col/v1",
      "description": "Production server"
    }
  ],
  "tags": [
    {
      "name": "Empresas",
      "description": "Endpoints para la gestión de empresas"
    }
  ],
  "paths": {
    "/companies": {
      "post": {
        "summary": "Endpoint para dar de alta a una empresa",
        "description": "Este endpoint permite dar de alta empresas en la API con las configuraciones necesarias para enviar documentos a la DIAN",
        "operationId": "createCompany",
        "tags": [
          "Empresas"
        ],
        "requestBody": {
          "description": "Objeto JSON con la información de la empresa",
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "allOf": [
                  {
                    "$ref": "#/paths/~1company/patch/requestBody/content/application~1json/schema"
                  },
                  {
                    "type": "object",
                    "required": [
                      "name",
                      "identification",
                      "dv",
                      "useAlegraCertificate"
                    ]
                  }
                ]
              },
              "examples": {
                "company": {
                  "summary": "Ejemplo para crear una empresa con la información basica",
                  "value": {
                    "name": "Soluciones Alegra S.A.S",
                    "identification": "11111111",
                    "dv": "2",
                    "econimicActivities": [
                      "0161",
                      "0150"
                    ],
                    "useAlegraCertificate": "false",
                    "certificate": {
                      "name": "certificado digital",
                      "extension": "pfx",
                      "content": "MIIdAgIBAzCCHMgGCSqGSIb3DQEHAaCCHLkEghy1.....A=",
                      "password": "12345"
                    },
                    "webhooks": {
                      "general": {
                        "governmentStatusChanged": {
                          "url": "https://my-webhook-test.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      },
                      "payrolls": {
                        "emissionFinished": {
                          "url": "https://my-webhook-test.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      },
                      "invoices": {
                        "emissionFinished": {
                          "url": "https://my-webhook-test-fe.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      },
                      "creditNotes": {
                        "emissionFinished": {
                          "url": "https://my-webhook-test-nc.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      },
                      "debitNotes": {
                        "emissionFinished": {
                          "url": "https://my-webhook-test-nd.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      },
                      "equivalentDocuments": {
                        "emissionFinished": {
                          "url": "https://my-webhook-test-de.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      },
                      "supportDocuments": {
                        "emissionFinished": {
                          "url": "https://my-webhook-test-de.com",
                          "headers": {
                            "x-api-key": "test-api-key"
                          },
                          "status": "active"
                        }
                      }
                    },
                    "organizationType": 1,
                    "regimeCode": "R-99-PN",
                    "taxCode": {
                      "id": "01"
                    },
                    "email": "email@email.com",
                    "address": {
                      "address": "Cra. 13 #12-12 Edificio A & A",
                      "city": "11001",
                      "department": "11",
                      "country": "CO"
                    }
                  }
                }
              }
            }
          }
        },
        "responses": {
          "200": {
            "$ref": "#/paths/~1company/get/responses/200"
          },
          "400": {
            "$ref": "#/components/responses/ValidationError"
          },
          "404": {
            "$ref": "#/components/responses/NotFoundError"
          },
          "500": {
            "$ref": "#/components/responses/InternalServerError"
          }
        },
        "security": [
          {
            "auth": []
          }
        ]
      },
      "get": {
        "summary": "Endpoint para consultar el listado de empresas",
        "description": "Retorna el listado de empresas asociadas al token",
        "operationId": "getCompanies",
        "tags": [
          "Empresas"
        ],
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "description": "Cantidad de resultados a obtener, por defecto es 50.",
            "schema": {
              "type": "integer",
              "minimum": 1,
              "maximum": 80
            }
          },
          {
            "name": "from",
            "in": "query",
            "description": "Id de la empresa a partir de la cual se desea iniciar la consulta. Se ignora si se envía `identification`.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "identification",
            "in": "query",
            "description": "NIT por el cual filtrar las empresas del usuario autenticado. Debe enviarse **sin dígito de verificación (DV)** — solo el número de identificación. Cuando se envía, solo se retornan las empresas del propio usuario cuya identificación coincida; el parámetro `from` se ignora en este modo.",
            "schema": {
              "type": "string",
              "minLength": 1,
              "maxLength": 20
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Objeto que representa la respuesta cuando se consultan el listado de empresas",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "metadata": {
                      "type": "object",
                      "properties": {
                        "from": {
                          "type": "string",
                          "description": "Id de la empresa desde la cual se inició la consulta"
                        },
                        "to": {
                          "type": "string",
                          "description": "Id de la última empresa en la página actual. Usar como valor de 'from' para obtener la siguiente página"
                        },
                        "results_count": {
                          "type": "number",
                          "description": "Cantidad de empresas en la página actual"
                        }
                      }
                    },
                    "companies": {
                      "type": "array",
                      "description": "Array con empresas",
                      "items": {
                        "type": "object",
                        "required": [
                          "name",
                          "identification",
                          "dv",
                          "useAlegraCertificate"
                        ],
                        "properties": {
                          "name": {
                            "type": "string",
                            "description": "Nombre/Razón Social de la empresa"
                          },
                          "tradeName": {
                            "type": "string",
                            "description": "Nombre Comercial de la empresa"
                          },
                          "identification": {
                            "type": "string",
                            "description": "Identificación de la empresa"
                          },
                          "dv": {
                            "type": "string",
                            "description": "Dígito verificador de la identificación de la empresa",
                            "pattern": "^([0-9]{1})$"
                          },
                          "useAlegraCertificate": {
                            "type": "boolean",
                            "description": "True si deseas usar el certificado de Alegra"
                          },
                          "governmentStatus": {
                            "type": "object",
                            "description": "Objeto que contiene la información de los estados de la compañía ante la DIAN para cada uno de los documentos electrónicos",
                            "properties": {
                              "payrolls": {
                                "type": "string",
                                "description": "Indica el estado de la compañía ante la DIAN para nómina electrónica",
                                "enum": [
                                  "AUTHORIZED",
                                  "UNAUTHORIZED",
                                  "IN_PROCESS"
                                ]
                              },
                              "invoices": {
                                "type": "string",
                                "description": "Indica el estado de la compañía ante la DIAN para factura electrónica",
                                "enum": [
                                  "AUTHORIZED",
                                  "UNAUTHORIZED",
                                  "IN_PROCESS"
                                ]
                              }
                            }
                          },
                          "certificate": {
                            "type": "object",
                            "description": "Objeto que contiene la información del certificado, obligatorio únicamente si el atributo useAlegraCertificate es false",
                            "properties": {
                              "name": {
                                "type": "string",
                                "description": "Nombre del archivo"
                              },
                              "extension": {
                                "type": "string",
                                "description": "Extensión del archivo"
                              },
                              "content": {
                                "type": "string",
                                "format": "byte",
                                "description": "Archivo de certificado en base 64"
                              },
                              "password": {
                                "type": "string",
                                "description": "Contraseña del certificado"
                              }
                            },
                            "required": [
                              "name",
                              "extension",
                              "content",
                              "password"
                            ]
                          },
                          "notificationByEmail": {
                            "type": "object",
                            "properties": {
                              "enabled": {
                                "type": "boolean",
                                "description": "Indica si se quiere enviar un email de notificación automáticamente después de que la empresa genere un documento electrónico valido. Valido para Factura Electrónica, Nota Débito y Nota Crédito. Por defecto es false"
                              },
                              "message": {
                                "type": "string",
                                "description": "Mensaje (opcional) que será añadido al final de la plantilla del correo"
                              }
                            },
                            "required": [
                              "enabled"
                            ]
                          },
                          "webhooks": {
                            "type": "object",
                            "description": "Objeto que contiene la información de los webhooks configurados para la empresa",
                            "properties": {
                              "general": {
                                "type": "object",
                                "description": "Objeto con información de webhooks generales",
                                "properties": {
                                  "governmentStatusChanged": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando cambia el estado de la compañía ante la DIAN",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                },
                                "required": [
                                  "governmentStatusChanged"
                                ]
                              },
                              "payrolls": {
                                "type": "object",
                                "description": "Objeto con información de webhooks para nóminas electrónicas",
                                "properties": {
                                  "emissionFinished": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando finaliza el proceso de emisión de una nómina electrónica",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                },
                                "required": [
                                  "emissionFinished"
                                ]
                              },
                              "invoices": {
                                "type": "object",
                                "description": "Objeto con información de webhooks para facturas electrónicas",
                                "properties": {
                                  "emissionFinished": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando finaliza el proceso de emisión de una factura electrónica",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                },
                                "required": [
                                  "emissionFinished"
                                ]
                              },
                              "creditNotes": {
                                "type": "object",
                                "description": "Objeto con información de webhooks para notas crédito electrónicas",
                                "properties": {
                                  "emissionFinished": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando finaliza el proceso de emisión de una nota crédito electrónica",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                },
                                "required": [
                                  "emissionFinished"
                                ]
                              },
                              "debitNotes": {
                                "type": "object",
                                "description": "Objeto con información de webhooks para notas débito electrónicas",
                                "properties": {
                                  "emissionFinished": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando finaliza el proceso de emisión de una nota débito electrónica",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                },
                                "required": [
                                  "emissionFinished"
                                ]
                              },
                              "equivalentDocuments": {
                                "type": "object",
                                "description": "Objeto con webhooks de documentos equivalentes electrónicos",
                                "properties": {
                                  "emissionFinished": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando finaliza el proceso de emisión de un documento equivalente electrónico",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                }
                              },
                              "supportDocuments": {
                                "type": "object",
                                "description": "Objeto con webhooks de documentos soporte electrónicos",
                                "properties": {
                                  "emissionFinished": {
                                    "type": "object",
                                    "description": "Objeto con la información para el webhook que se dispara cuando finaliza el proceso de emisión de un documento soporte electrónico",
                                    "properties": {
                                      "url": {
                                        "type": "string",
                                        "description": "Url a la cual notificará el webhook"
                                      },
                                      "headers": {
                                        "type": "object",
                                        "description": "Objeto con headers personalizados que serán enviados en el request al webhook configurado"
                                      },
                                      "status": {
                                        "type": "string",
                                        "enum": [
                                          "active",
                                          "inactive"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "url"
                                    ]
                                  }
                                }
                              }
                            }
                          },
                          "organizationType": {
                            "type": "number",
                            "description": "Identificador de tipo de organización jurídica de la persona o empresa. Se debe colocar el Código que corresponda de la tabla de tipos de organización jurídica de la DIAN. <br><i>Campo oficial DIAN &lt;AdditionalAccountID&gt;</i>",
                            "maxLength": 1
                          },
                          "identificationType": {
                            "type": "string",
                            "description": "Tipo de documento de identificación de la empresa. Se debe colocar el Código que corresponda de la tabla de tipos de identificación de la DIAN",
                            "maxLength": 2
                          },
                          "regimeCode": {
                            "type": "string",
                            "description": "Régimen al que pertenece la empresa. Se debe colocar el Código que corresponda de la tabla de tipos de régimen/responsabilidades fiscales de la DIAN. Para reportar varias obligaciones / responsabilidades, se deben reportar separando cada uno de los valores de la lista con ';'. Ejemplo O‐13;O‐15;"
                          },
                          "taxCode": {
                            "type": "object",
                            "description": "Objeto que contiene el grupo de detalles tributarios del Emisor",
                            "properties": {
                              "id": {
                                "type": "string",
                                "description": "Identificador del tributo."
                              },
                              "name": {
                                "type": "string",
                                "description": "Nombre del tributo o nombre de la figura tributaria. Se debe enviar en caso de que el identificador del tributo sea 'ZZ'"
                              }
                            },
                            "required": [
                              "id"
                            ]
                          },
                          "email": {
                            "type": "string",
                            "description": "Correo electrónico de la empresa. Se debe colocar el correo de recepción para documentos e instrumentos electrónicos"
                          },
                          "phone": {
                            "type": "string",
                            "description": "Número de teléfono, celular u otro"
                          },
                          "address": {
                            "$ref": "#/components/schemas/AddressDataFE"
                          }
                        }
                      }
                    }
                  }
                },
                "examples": {
                  "get-companies": {
                    "summary": "Ejemplo de respuesta que contiene una lista de empresas",
                    "value": {
                      "count": 2,
                      "companies": [
                        {
                          "id": "PzBrB1ppclOZwqFxa29F",
                          "name": "Soluciones Alegra S.A.S",
                          "identification": "111111111",
                          "dv": "2",
                          "useAlegraCertificate": false,
                          "governmentStatus": {
                            "payrolls": "AUTHORIZED"
                          },
                          "certificate": {
                            "name": "certificado digital",
                            "extension": "pfx",
                            "issuerName": "emailAddress = info@andesscd.com.co, CN = CA ANDES SCD S.A. Clase II, OU = Division de certificacion entidad final, O = Andes SCD., L = Bogota D.C., C = CO",
                            "startDate": "2019-05-28 15:36:00",
                            "endDate": "2021-05-27 15:35:00",
                            "serialNumber": "11111111"
                          },
                          "webhooks": {
                            "general": {
                              "governmentStatusChanged": {
                                "url": "https://my-webhook-test.com",
                                "headers": {
                                  "x-api-key": "test-api-key"
                                },
                                "status": "active"
                              }
                            },
                            "payrolls": {
                              "emissionFinished": {
                                "url": "https://my-webhook-test.com",
                                "headers": {
                                  "x-api-key": "test-api-key"
                                },
                                "status": "active"
                              }
                            }
                          },
                          "organizationType": 1,
                          "identificationType": "31",
                          "regimeCode": "R-99-PN",
                          "email": "email@email.com",
                          "address": {
                            "address": "Cra. 13 #12-12 Edificio A & A",
                            "city": "11001",
                            "department": "11",
                            "country": "CO"
                          }
                        },
                        {
                          "id": "PzBrB1ppclOZwqFxa29F",
                          "name": "Soluciones Alegra S.A.S",
                          "identification": "111111111",
                          "dv": "2",
                          "useAlegraCertificate": false,
                          "governmentStatus": {
                            "payrolls": "AUTHORIZED"
                          },
                          "certificate": {
                            "name": "certificado digital",
                            "extension": "pfx",
                            "issuerName": "emailAddress = info@andesscd.com.co, CN = CA ANDES SCD S.A. Clase II, OU = Division de certificacion entidad final, O = Andes SCD., L = Bogota D.C., C = CO",
                            "startDate": "2019-05-28 15:36:00",
                            "endDate": "2021-05-27 15:35:00",
                            "serialNumber": "11111111"
                          },
                          "webhooks": {
                            "general": {
                              "governmentStatusChanged": {
                                "url": "https://my-webhook-test.com",
                                "headers": {
                                  "x-api-key": "test-api-key"
                                },
                                "status": "active"
                              }
                            },
                            "payrolls": {
                              "emissionFinished": {
                                "url": "https://my-webhook-test.com",
                                "headers": {
                                  "x-api-key": "test-api-key"
                                },
                                "status": "active"
                              }
                            }
                          },
                          "organizationType": 1,
                          "identificationType": "31",
                          "regimeCode": "R-99-PN",
                          "email": "email@email.com",
                          "address": {
                            "address": "Cra. 13 #12-12 Edificio A & A",
                            "city": "11001",
                            "department": "11",
                            "country": "CO"
                          }
                        }
                      ]
                    }
                  }
                }
              }
            }
          },
          "400": {
            "$ref": "#/components/responses/ValidationError"
          },
          "404": {
            "$ref": "#/components/responses/NotFoundError"
          },
          "500": {
            "$ref": "#/components/responses/InternalServerError"
          }
        },
        "security": [
          {
            "auth": []
          }
        ]
      }
    }
  },
  "components": {
    "schemas": {
      "Error": {
        "type": "object",
        "description": "Objeto que representa un error en el sistema",
        "required": [
          "message"
        ],
        "properties": {
          "code": {
            "type": "string",
            "description": "Código de error"
          },
          "message": {
            "type": "string",
            "description": "Mensaje de error"
          }
        }
      },
      "AddressDataFE": {
        "type": "object",
        "description": "Objeto que contiene la información relacionada a la dirección. <br><i>Grupo de información oficial DIAN &lt;RegistrationAddress | PhysicalLocation&gt;</i>",
        "properties": {
          "address": {
            "type": "string",
            "description": "Dirección del lugar fisico. <br><i>Campo oficial DIAN &lt;Line&gt;</i>"
          },
          "city": {
            "type": "string",
            "description": "Código de la Ciudad. Se debe colocar el Código que corresponda de la tabla de municipios disponibles de la DIAN. Se debe informar cuando el código del País es 'CO'. <br><i>Campo oficial DIAN &lt;ID&gt;</i>",
            "maxLength": 5
          },
          "department": {
            "type": "string",
            "description": "Código del Departamento. Se debe colocar el Código que corresponda de la tabla de departamentos disponibles de la DIAN. Se debe informar cuando el código del País es 'CO'. <br><i>Campo oficial DIAN &lt;CountrySubentityCode&gt;</i>",
            "maxLength": 2
          },
          "country": {
            "type": "string",
            "description": "Código identificador del País. Se debe colocar el código que corresponda de la tabla de países disponibles de la DIAN. Por defecto 'CO'. <br><i>Campo oficial DIAN &lt;IdentificationCode&gt;</i>"
          }
        }
      }
    },
    "responses": {
      "ValidationError": {
        "description": "Objeto que representa una respuesta de error por validaciones",
        "content": {
          "application/json": {
            "schema": {
              "type": "array",
              "description": "Array que contiene N errores generados en el sistema",
              "items": {
                "$ref": "#/components/schemas/Error"
              }
            }
          }
        }
      },
      "NotFoundError": {
        "description": "Objeto que representa una respuesta de error por qué no se ha encontrado el recurso al que se intenta acceder",
        "content": {
          "application/json": {
            "schema": {
              "type": "array",
              "description": "Array que contiene N errores generados en el sistema",
              "items": {
                "$ref": "#/components/schemas/Error"
              }
            }
          }
        }
      },
      "InternalServerError": {
        "description": "Objeto que representa una respuesta de error por qué ha ocurrido un error interno en el sistema",
        "content": {
          "application/json": {
            "schema": {
              "type": "array",
              "description": "Array que contiene N errores generados en el sistema",
              "items": {
                "$ref": "#/components/schemas/Error"
              }
            }
          }
        }
      }
    },
    "securitySchemes": {
      "auth": {
        "type": "http",
        "scheme": "bearer"
      }
    }
  }
}
```