"""
Una biblioteca tiene un sistema de préstamo de libros, y ofrece a sus usuarios 
la posibilidad de coger prestado o devolver un libro. Los libros están identificados por un número del 1 al 10.

Usando monitores y condiciones de sincronización para la gestión de la biblioteca
e hilos para el cada usuario, escribe un programa que:

Gestione el prestamo de libros, marcando el libro prestado como no disponible hasta que se devuelva.
Lance 20 procesos lectores. Cada hilo pide un libro aleatorio, luego tarda un tiempo aleatorio en devolverlo. 
Si el libro no está disponible, el hilo quedará esperando a que se devuelva.
"""

# Importamos las librerías necesarias
import random as rd
import time 
from threading import Lock, Condition, Thread

# En primer lugar vamos a crear la biblioteca:
class Biblioteca:
    def __init__(self):
        # Definimos los 10 libros disponibles en la biblioteca
        # self.libros = {i: True for i in range(1,11)}
        self.libros = {1: True,
                                     2: True,
                                     3: True,
                                     4: True,
                                     5: True,
                                     6: True,
                                     7: True,
                                     8: True,
                                     9: True,
                                     10: True}
        # Definimos la condición que más tarde crearemos
        self.condition = Condition()
        
    # Creamos el método con el que cogemos un libro prestado
    def coger_libro(self, libro_id: int, hilo_id:int) -> None:
        # Adquirimos el cerrojo
        with self.condition:
            # Hacemos que el hilo espera hasta que esté disponible
            while self.libros[libro_id] == False:
                print(f"El libro está prestado, espere hilo nº{hilo_id}")
                self.condition.wait()
            # Cuando está disponible coge el libro nuestro hilo y cambiamos el estado
            self.libros[libro_id] = False
            print(f"El libro ha sido prestado éxitosamente al hilo nº{hilo_id}")
                
    # Definimos el método para devolver un libro a la librería
    def devolver_libro(self,libro_id:int,hilo_id:int) -> None:
        # Adquirimos el cerrojo
        with self.condition:
            # Hacemos que el hilo devuelva nuestro libro
            self.libros[libro_id] = True
            print(f"El libro ha sido leido y devuelto éxitosamente por el hilo nº {hilo_id}")
            self.condition.notify_all()
            
# Definimos la función que elegirá los libros aleatorios y procesa los 20 hilos
def random_library(libreria:Biblioteca, hilo_id:int) -> None:
    # Elegimos un libro aleatorio
    libro_id = rd.randint(1,10)
    print(f"El hilo nº{hilo_id} quier el libro  {libro_id}")
    # El hilo coge el libro
    libreria.coger_libro(libro_id,hilo_id)
    # El hilo "lee" el libro
    time.sleep(rd.uniform(0.5,2.0))
    # El hilo devuelve el libro
    libreria.devolver_libro(libro_id,hilo_id)
    
if __name__ == "__main__":
    # Creamos la biblioteca y los hilos
    library = Biblioteca()
    hilos =[]
    # Tenemos en cuenta el tiempo que se tarda en procesar la ejecución
    start = time.time()
    # Creamos los 20 hilos
    for i in range(20):
        hilo = Thread(
            target = random_library,
            args = (library,i)
        )
        hilos.append(hilo)
        hilo.start()
    # Ahora unimos los hilos
    for hilo in hilos:
        hilo.join()
    # Finalizamos el tiempo
    end = time.time()
    final_time = round(end-start,2)
    print (f"Los {len(hilos)} hilos han leido y devuelto sus libros a la biblioteca en un tiempo de: {final_time} segundos")