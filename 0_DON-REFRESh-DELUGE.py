import requests
from bs4 import BeautifulSoup
import os
import sys
import re
import readchar
from time import sleep
import json
from urllib.parse import urljoin
import base64

# Configuración Deluge
DELUGE_URL = "LOCAL URL TO DELUGE"
# EXAMPLE DELUGE_URL = "http://192.168.1.107:8112/json"
DELUGE_PASSWORD = "PASSWORDDELUGE"
HEADERS = {'Content-Type': 'application/json'}

# Configuración de la interfaz
BORDER_COLOR = "\033[34m"  # Azul
RESET_COLOR = "\033[0m"
BORDER_CHAR = "═"
VERTICAL_BORDER = "║"
CORNER_CHAR = "╔╗╝╚"

def debug_log(message):
    """Función para depuración (puedes activarla/desactivarla)"""
    DEBUG = True  # Cambia a False para desactivar los logs de depuración
    if DEBUG:
        with open("debug.log", "a") as f:
            f.write(f"{message}\n")

def draw_window(title, content_lines, width=80, height=20):
    """Dibuja una ventana con bordes al estilo SPF"""
    term_width = os.get_terminal_size().columns - 4
    width = min(width, term_width)
    
    top_border = BORDER_COLOR + CORNER_CHAR[0] + BORDER_CHAR * (width-2) + CORNER_CHAR[1] + RESET_COLOR
    bottom_border = BORDER_COLOR + CORNER_CHAR[3] + BORDER_CHAR * (width-2) + CORNER_CHAR[2] + RESET_COLOR
    empty_line = BORDER_COLOR + VERTICAL_BORDER + RESET_COLOR + " " * (width-2) + BORDER_COLOR + VERTICAL_BORDER + RESET_COLOR
    
    title_line = (BORDER_COLOR + VERTICAL_BORDER + RESET_COLOR + 
                 f" {title.center(width-4)} " + 
                 BORDER_COLOR + VERTICAL_BORDER + RESET_COLOR)
    
    content = []
    for line in content_lines:
        content.append(BORDER_COLOR + VERTICAL_BORDER + RESET_COLOR + 
                      f" {line.ljust(width-4)} " + 
                      BORDER_COLOR + VERTICAL_BORDER + RESET_COLOR)
    
    while len(content) < height - 4:
        content.append(empty_line)
    
    return [top_border, title_line] + content + [bottom_border]

def show_interface():
    """Muestra la interfaz completa"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    main_title = "CINE DONTORRENT"
    main_content = [
        "Selecciona películas con ↑/↓",
        "Dominio DonTorrenT:",
        ">",
        "R Refrescar Q Salir"
    ]
    print("\n".join(draw_window(main_title, main_content, height=8)))

def show_movie_list(titles, selected_index):
    """Muestra la lista de películas"""
    content = []
    for i, title in enumerate(titles):
        prefix = "→" if i == selected_index else " "
        title_text = title.split('/')[-1].replace('-', ' ')
        content.append(f"{prefix} {title_text}")
    
    print("\n".join(draw_window("ÚLTIMAS PELÍCULAS", content, height=len(titles)+4)))

def clear_screen():
    """Limpia la pantalla mostrando la interfaz"""
    show_interface()

def get_domain():
    """Solicita el dominio con interfaz SPF"""
    while True:
        clear_screen()
        
        config_content = [
            "<>:",
            "Ejemplo: https://dontorrent.website",
            ""  # Línea vacía para el input
        ]
        config_window = draw_window("CONFIGURACIÓN", config_content, height=7)
        
        print("\n".join(config_window))
        print("\033[5;4H> ", end="", flush=True)
        
        domain = input().strip()
        
        if not domain:
            continue
            
        if not domain.startswith('http'):
            domain = f"https://{domain}"
            
        domain = re.sub(r'(https?://[^/]+)/?.*', r'\1', domain)
        
        try:
            debug_log(f"Probando conexión con: {domain}/descargar-peliculas")
            response = requests.head(f"{domain}/descargar-peliculas", timeout=5)
            debug_log(f"Respuesta HTTP: {response.status_code}")
            
            if response.status_code == 200:
                return domain
            show_error_window(["Error HTTP", f"Código: {response.status_code}", "Presione Enter..."])
        except Exception as e:
            debug_log(f"Error al conectar: {str(e)}")
            show_error_window([f"Error: {str(e)}", "Presione Enter..."])

def show_error_window(content):
    """Muestra ventana de error"""
    print("\n".join(draw_window("ERROR", content)))
    input()

def get_movie_titles(base_url):
    """Obtiene los títulos de las películas"""
    try:
        debug_log(f"Obteniendo títulos de: {base_url}/descargar-peliculas")
        response = requests.get(f"{base_url}/descargar-peliculas", timeout=10)
        debug_log(f"Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            movie_links = soup.find_all('a', href=lambda href: href and "/pelicula/" in href)
            debug_log(f"Encontrados {len(movie_links)} enlaces de películas")
            
            absolute_urls = []
            for link in movie_links[:20]:
                href = link['href']
                absolute_urls.append(href if href.startswith('http') else f"{base_url}{href}")
            
            return absolute_urls
        return []
    except Exception as e:
        debug_log(f"Error al obtener títulos: {str(e)}")
        return []

def get_torrent_url(movie_url, base_domain):
    """Obtiene la URL del torrent"""
    try:
        debug_log(f"Buscando torrent en: {movie_url}")
        response = requests.get(movie_url, timeout=10)
        debug_log(f"Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            torrent_link = soup.find('a', href=lambda href: href and (href.endswith('.torrent') or 'torrents/peliculas/' in href))
            
            if torrent_link:
                href = torrent_link['href']
                debug_log(f"Enlace torrent encontrado: {href}")
                
                if href.startswith('//'):
                    return f"https:{href}"
                elif href.startswith('/'):
                    return f"{base_domain}{href}"
                elif not href.startswith('http'):
                    return f"{base_domain}/torrents/peliculas/{href}"
                return href
        return None
    except Exception as e:
        debug_log(f"Error al obtener torrent: {str(e)}")
        return None

def download_torrent(url, filename):
    """Descarga el archivo torrent"""
    try:
        debug_log(f"Descargando torrent: {url}")
        response = requests.get(url, stream=True, timeout=30)
        debug_log(f"Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            debug_log(f"Torrent guardado como: {filename}")
            return True
        return False
    except Exception as e:
        debug_log(f"Error al descargar torrent: {str(e)}")
        return False

def add_to_deluge(torrent_file):
    """Añade un torrent a Deluge con mejor manejo de errores"""
    try:
        debug_log(f"Intentando subir torrent: {torrent_file}")
        
        # Primero autenticamos
        auth_payload = {
            "id": 1,
            "method": "auth.login",
            "params": [DELUGE_PASSWORD]
        }
        
        auth_response = requests.post(
            DELUGE_URL,
            data=json.dumps(auth_payload),
            headers=HEADERS,
            timeout=10
        )
        
        if auth_response.status_code != 200 or not auth_response.json().get("result"):
            return False, "Error de autenticación en Deluge"
        
        cookies = auth_response.cookies
        
        # Leemos el contenido del torrent
        with open(torrent_file, 'rb') as f:
            torrent_content = f.read()
        
        # Codificamos el contenido en base64
        torrent_data = base64.b64encode(torrent_content).decode('utf-8')
        
        # Añadimos el torrent
        add_payload = {
            "id": 2,
            "method": "core.add_torrent_file",
            "params": [
                os.path.basename(torrent_file),
                torrent_data,
                {}  # Opciones (vacío por defecto)
            ]
        }
        
        add_response = requests.post(
            DELUGE_URL,
            data=json.dumps(add_payload),
            headers=HEADERS,
            cookies=cookies,
            timeout=10
        )
        
        if add_response.status_code != 200:
            return False, f"Error al añadir torrent (HTTP {add_response.status_code})"
        
        result = add_response.json().get("result")
        if result:
            return True, "Torrent añadido correctamente"
        else:
            return False, "El servidor rechazó el torrent"
            
    except requests.exceptions.Timeout:
        return False, "Timeout al comunicarse con Deluge"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def handle_movie_selection(movie_url, base_domain):
    """Maneja la selección de una película"""
    movie_name = movie_url.split('/')[-1].replace('-', ' ')
    torrent_filename = f"{movie_name.replace(' ', '_')}.torrent"
    
    print("\n".join(draw_window("PROCESANDO", [
        f"Obteniendo torrent para:",
        f"{movie_name}...",
        "",
        "Por favor espere..."
    ])))
    
    torrent_url = get_torrent_url(movie_url, base_domain)
    if not torrent_url:
        print("\n".join(draw_window("ERROR", [
            "No se encontró enlace torrent",
            "Intente manualmente:",
            movie_url,
            "",
            "Presione Enter para continuar..."
        ])))
        input()
        return
    
    # Descargar el torrent localmente
    if not download_torrent(torrent_url, torrent_filename):
        print("\n".join(draw_window("ERROR", [
            "Error en la descarga",
            "Intente manualmente:",
            torrent_url,
            "",
            "Presione Enter para continuar..."
        ])))
        input()
        return
    
    # Enviar a Deluge
    print("\n".join(draw_window("PROCESANDO", [
        "Enviando torrent a Deluge...",
        "",
        "Por favor espere..."
    ])))
    
    success, message = add_to_deluge(torrent_filename)
    
    if success:
        result_content = [
            "¡Operación completada!",
            message,
            f"Archivo: {torrent_filename}",
            "",
            "Presione Enter para continuar..."
        ]
    else:
        result_content = [
            "Descarga local completada pero",
            "falló el envío a Deluge:",
            message,
            f"Archivo local: {torrent_filename}",
            "",
            "Presione Enter para continuar..."
        ]
    
    print("\n".join(draw_window("RESULTADO", result_content)))
    input()

def show_goodbye_message():
    """Muestra mensaje de despedida"""
    clear_screen()
    print("\n".join(draw_window("SALIENDO", [
        "Gracias por usar Cine Torrent Downloader",
        "",
        "Hasta pronto!"
    ], height=7)))

def main():
    try:
        import readchar
        debug_log("Iniciando aplicación...")
        
        base_domain = get_domain()
        movie_urls = get_movie_titles(base_domain)
        
        if not movie_urls:
            show_error_window(["No se pudieron obtener títulos", "Verifique su conexión"])
            return
        
        selected_index = 0
        while True:
            clear_screen()
            show_movie_list(movie_urls, selected_index)
            
            key = readchar.readkey()
            if key == readchar.key.UP:
                selected_index = max(0, selected_index - 1)
            elif key == readchar.key.DOWN:
                selected_index = min(len(movie_urls) - 1, selected_index + 1)
            elif key in (readchar.key.ENTER, '\n'):
                handle_movie_selection(movie_urls[selected_index], base_domain)
            elif key.lower() == 'r':  # Tecla R para refrescar
                print("\n".join(draw_window("ACTUALIZANDO", ["Obteniendo lista actualizada..."])))
                sleep(1)
                movie_urls = get_movie_titles(base_domain)
                if not movie_urls:
                    show_error_window(["No se pudieron actualizar los títulos", "Verifique su conexión"])
            elif key.lower() == 'q':
                break
                
        show_goodbye_message()
    except ImportError as e:
        show_error_window(["Se requiere readchar", "Instale con: pip install readchar"])
        debug_log(f"Error de importación: {str(e)}")
        sys.exit(1)
    except Exception as e:
        show_error_window(["Error inesperado:", str(e)])
        debug_log(f"Error inesperado en main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import json
    except ImportError:
        print("Error: Se requiere el módulo 'json'")
        sys.exit(1)
    
    # Limpiar archivo de log al inicio
    open("debug.log", "w").close()
    
    main()

