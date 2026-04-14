# Grupo-Q 
# Marc Martínez Arias
# Pedro Barros Bobadilla
# URL: https://github.com/Code-Cram/PROGRAMACION_CONCURRENTE_Y_DISTRIBUIDA_Grupo_Q


"""
El taller de bicicletas

Para crear este taller de forma precisa tenemos que tener en cuenta que
para crear una bicivleta necesitamos dos ruedas y un marco. Estas piezas
han de ser creadas y almacenadas. Los almacenes de los que dispone el taller
solo tienen una capacidad de 10 ruedas y 4 marcos. Para crear este taller vamos
a implementar procesos como trabajadores.

Cada trabajador tiene un oficio específico, esto quiere decir que hay un
constructor de ruedas, un constructor de marcos y un montador de bicicletas.
Todos estos trabajadores una vez terminan su trabajo lo guardan en el almacen del taller.

Importante tener en cuenta que el operario que fabrica marcos no tiene espacio para 
almacenar más de 4 marcos y el operario que fabrica ruedas no puede almacenar más de 10 ruedas.

Usando procesos y comunicación mediante paso de mensajes (colas), implementamos
un taller distribuido que respeta estas restricciones.
"""

from multiprocessing import Process, Queue
from typing import Literal

# Proceso que genera piezas de un tipo ("rueda" o "marco")
class GeneradorPiezas:
    # Iniciamos el constructor de clases
    def __init__(self, tipo: Literal["rueda", "marco"], cantidad: int,cola_almacen: Queue,id_generador: int,) -> None:
        self.tipo = tipo
        self.cantidad = cantidad
        self.cola_almacen = cola_almacen
        self.id_generador = id_generador

    # Definimos el método público que inicia el proceso de crear un material
    def run(self) -> None:
        # Creamos el item y lo guardamos en la cola correspondiente.
        for _ in range(self.cantidad):
            self.cola_almacen.put(self.tipo)
            print(f"{self.id_generador} ha creado el item {self.tipo}")

    # Métodos públicos básicos para el correcto uso de los procesos.
    # Una equivalencia es como si ficharan los trabajadores en el almacén.
    def start(self) -> None:
        self.proceso = Process(target=self.run)
        self.proceso.start()

    def join(self) -> None:
        self.proceso.join()


# Clase que define el proceso que monta las bicicletas
class Montador:
    # Iniciamos el constructor de clase
    def __init__(self, cantidad_bicicletas: int, cola_ruedas: Queue, cola_marcos: Queue, id_montador: int) -> None:
        self.cantidad_bicicletas = cantidad_bicicletas
        self.cola_ruedas = cola_ruedas
        self.cola_marcos = cola_marcos
        self.id_montador = id_montador
    # Definimos el método público que inicia el proceso de la creación de la bicicleta
    def run(self) -> None:
        for i in range(1, self.cantidad_bicicletas + 1):
            # Tomamos dos ruedas
            self.cola_ruedas.get()
            self.cola_ruedas.get()
            # Tomamos un marco
            self.cola_marcos.get()
            # Montamos la bicicleta
            print(f"{self.id_montador} monta la bicicleta #{i}")

    def start(self) -> None:
        self.proceso = Process(target=self.run)
        self.proceso.start()

    def join(self) -> None:
        self.proceso.join()


# Creamos el taller que distribuye los procesos y los almacenes de los items.
class Taller:
    # Iniciamos el constructor de clases
    def __init__(self) -> None:
        # Colas que actúan como almacenes con capacidad limitada
        self.cola_ruedas = Queue(maxsize=10)  # máximo 10 ruedas almacenadas
        self.cola_marcos = Queue(maxsize=4)   # máximo 4 marcos almacenados

        # Decidimos cuántas bicicletas queremos montar.
        # Para n bicicletas necesitamos 2n ruedas y n marcos.
        n_bicicletas = 4

        # Generador de ruedas: 2 * n_bicicletas ruedas, respetando el límite 10.
        self.generador_ruedas = GeneradorPiezas(
            tipo="rueda",
            cantidad=2 * n_bicicletas,
            cola_almacen=self.cola_ruedas,
            id_generador=1,
        )

        # Generador de marcos: n_bicicletas marcos, respetando el límite 4.
        self.generador_marcos = GeneradorPiezas(
            tipo="marco",
            cantidad=n_bicicletas,
            cola_almacen=self.cola_marcos,
            id_generador=2,
        )

        # Montador: intenta montar n_bicicletas
        self.montador = Montador(
            cantidad_bicicletas=n_bicicletas,
            cola_ruedas=self.cola_ruedas,
            cola_marcos=self.cola_marcos,
            id_montador=1,
        )
    # Definimos el método público que realiza todos los procesos del taller
    def start(self) -> None:
        # Inicia los procesos. Es decir, los operarios empiezan a trabajar.
        print("Se arranca el taller")
        self.generador_ruedas.start()
        self.generador_marcos.start()
        self.montador.start()
    # Definimos el método público básico para el procesamiento de los procesos
    def join(self) -> None:
        self.generador_ruedas.join()
        self.generador_marcos.join()
        self.montador.join()
        print("Producción terminada")

if __name__ == "__main__":
    taller = Taller()
    taller.start()
    taller.join()