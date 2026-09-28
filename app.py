from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
from functools import wraps
from werkzeug.security import check_password_hash
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from extensions import db
from models.sorteo import Sorteo
from models.numero import Numero
from models.participacion import Participacion
from models.pago import Pago
from models.multimedia import Multimedia
from models.pack import Pack
from servicios.vencimientos import liberar_participaciones_vencidas
from servicios.mercado_pago import crear_preferencia, consultar_pago
from servicios.procesar_pagos import procesar_pago_aprobado
from servicios.archivos import guardar_imagen
from servicios.videos import preparar_video

import os
import random
from datetime import timedelta
from servicios.fechas import ahora_utc

load_dotenv()

csrf = CSRFProtect()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

database_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///sorteos.db"
)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
csrf.init_app(app)


@app.template_filter("moneda")
def formato_moneda(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return valor

    if numero.is_integer():
        return f"{int(numero):,}".replace(",", ".")

    entero, decimales = f"{numero:,.2f}".split(".")
    entero = entero.replace(",", ".")
    return f"{entero},{decimales}"


def admin_requerido(funcion):

    @wraps(funcion)
    def decorada(*args, **kwargs):

        if not session.get("admin_autenticado"):
            return redirect(url_for("admin_login"))

        return funcion(*args, **kwargs)

    return decorada


@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get("admin_autenticado"):
        return redirect(url_for("admin_sorteos"))

    error = None

    if request.method == "POST":

        usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        usuario_correcto = os.getenv(
            "ADMIN_USUARIO"
        )

        password_hash = os.getenv(
            "ADMIN_PASSWORD_HASH"
        )

        if (
            usuario_correcto
            and password_hash
            and usuario == usuario_correcto
            and check_password_hash(
                password_hash,
                password
            )
        ):

            session.clear()
            session["admin_autenticado"] = True

            return redirect(
                url_for("admin_sorteos")
            )

        error = "Usuario o contraseña incorrectos."

    return render_template(
        "admin_login.html",
        error=error
    )


@app.route("/admin/logout", methods=["POST"])
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


@app.context_processor
def utilidades_templates():
    return {
        "preparar_video": preparar_video
    }


@app.route("/")
def inicio():

    sorteos = Sorteo.query.filter_by(activo=True).all()

    for sorteo in sorteos:
        sorteo.numeros = Numero.query.filter_by(
            sorteo_id=sorteo.id
        ).all()

    return render_template(
        "index.html",
        sorteos=sorteos
    )


@app.route("/admin/sorteos")
@admin_requerido
def admin_sorteos():

    sorteos = Sorteo.query.order_by(
        Sorteo.id.desc()
    ).all()

    return render_template(
        "admin_sorteos.html",
        sorteos=sorteos
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/editar",
    methods=["GET", "POST"]
)
@admin_requerido
def editar_sorteo(sorteo_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    if request.method == "POST":

        titulo = request.form["titulo"].strip()
        descripcion = request.form["descripcion"].strip()

        if not titulo:
            return "El título es obligatorio.", 400

        sorteo.titulo = titulo
        sorteo.descripcion = descripcion

        sorteo.activo = (
            request.form.get("activo") == "on"
        )

        db.session.commit()

        return redirect(
            url_for("admin_sorteos")
        )

    return render_template(
        "editar_sorteo.html",
        sorteo=sorteo
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/fotos",
    methods=["GET", "POST"]
)
@admin_requerido
def administrar_fotos(sorteo_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    if request.method == "POST":

        url_video = request.form.get(
            "url_video",
            ""
        ).strip()

        if url_video:

            from urllib.parse import urlparse

            url_analizada = urlparse(url_video)

            if (
                url_analizada.scheme not in {"http", "https"}
                or not url_analizada.netloc
            ):
                flash(
                    "El enlace del video no es válido.",
                    "error"
                )

                return redirect(
                    url_for(
                        "administrar_fotos",
                        sorteo_id=sorteo.id
                    )
                )

            ultimo_video = Multimedia.query.filter_by(
                sorteo_id=sorteo.id,
                tipo="video"
            ).order_by(
                Multimedia.orden.desc()
            ).first()

            siguiente_orden_video = (
                ultimo_video.orden + 1
                if ultimo_video
                else 0
            )

            video = Multimedia(
                sorteo_id=sorteo.id,
                tipo="video",
                url=url_video,
                principal=False,
                orden=siguiente_orden_video
            )

            db.session.add(video)
            db.session.commit()

            flash(
                "Video agregado correctamente.",
                "exito"
            )

            return redirect(
                url_for(
                    "administrar_fotos",
                    sorteo_id=sorteo.id
                )
            )

        imagenes = request.files.getlist("imagenes")

        ultimo = Multimedia.query.filter_by(
            sorteo_id=sorteo.id,
            tipo="imagen"
        ).order_by(
            Multimedia.orden.desc()
        ).first()

        siguiente_orden = (
            ultimo.orden + 1
            if ultimo
            else 0
        )

        hay_imagen_principal = Multimedia.query.filter_by(
            sorteo_id=sorteo.id,
            tipo="imagen",
            principal=True
        ).first()

        imagenes_guardadas = 0

        for imagen in imagenes:

            if not imagen or not imagen.filename:
                continue

            try:

                ruta_imagen = guardar_imagen(
                    imagen,
                    sorteo.id
                )

                multimedia = Multimedia(
                    sorteo_id=sorteo.id,
                    tipo="imagen",
                    url=ruta_imagen,
                    principal=(
                        hay_imagen_principal is None
                        and imagenes_guardadas == 0
                    ),
                    orden=siguiente_orden
                )

                db.session.add(multimedia)

                siguiente_orden += 1
                imagenes_guardadas += 1

            except ValueError as error:
                flash(
                    f"No se pudo subir {imagen.filename}: {error}",
                    "error"
                )

        db.session.commit()

        if imagenes_guardadas > 0:
            flash(
                f"Se subieron {imagenes_guardadas} imagen(es) correctamente.",
                "exito"
            )

        return redirect(
            url_for(
                "administrar_fotos",
                sorteo_id=sorteo.id
            )
        )

    imagenes = Multimedia.query.filter_by(
        sorteo_id=sorteo.id,
        tipo="imagen"
    ).order_by(
        Multimedia.orden
    ).all()

    videos = Multimedia.query.filter_by(
        sorteo_id=sorteo.id,
        tipo="video"
    ).order_by(
        Multimedia.orden
    ).all()

    return render_template(
        "admin_fotos.html",
        sorteo=sorteo,
        imagenes=imagenes,
        videos=videos
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/videos/<int:video_id>/eliminar",
    methods=["POST"]
)
@admin_requerido
def eliminar_video(sorteo_id, video_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    video = Multimedia.query.filter_by(
        id=video_id,
        sorteo_id=sorteo.id,
        tipo="video"
    ).first_or_404()

    db.session.delete(video)
    db.session.commit()

    flash(
        "Video eliminado correctamente.",
        "exito"
    )

    return redirect(
        url_for(
            "administrar_fotos",
            sorteo_id=sorteo.id
        )
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/fotos/<int:foto_id>/principal",
    methods=["POST"]
)
@admin_requerido
def hacer_foto_principal(sorteo_id, foto_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    foto = Multimedia.query.filter_by(
        id=foto_id,
        sorteo_id=sorteo.id,
        tipo="imagen"
    ).first_or_404()

    imagenes = Multimedia.query.filter_by(
        sorteo_id=sorteo.id,
        tipo="imagen"
    ).order_by(
        Multimedia.orden
    ).all()

    # La elegida pasa primero.
    imagenes_ordenadas = [
        foto
    ] + [
        imagen
        for imagen in imagenes
        if imagen.id != foto.id
    ]

    # Dejamos una sola principal y
    # reordenamos desde cero.
    for orden, imagen in enumerate(
        imagenes_ordenadas
    ):
        imagen.principal = (
            imagen.id == foto.id
        )

        imagen.orden = orden

    db.session.commit()

    return redirect(
        url_for(
            "administrar_fotos",
            sorteo_id=sorteo.id
        )
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/fotos/<int:foto_id>/eliminar",
    methods=["POST"]
)
@admin_requerido
def eliminar_foto(sorteo_id, foto_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    foto = Multimedia.query.filter_by(
        id=foto_id,
        sorteo_id=sorteo.id,
        tipo="imagen"
    ).first_or_404()

    era_principal = foto.principal

    ruta_archivo = Path("static") / foto.url

    db.session.delete(foto)
    db.session.flush()

    if era_principal:

        nueva_principal = Multimedia.query.filter_by(
            sorteo_id=sorteo.id,
            tipo="imagen"
        ).order_by(
            Multimedia.orden
        ).first()

        if nueva_principal:
            nueva_principal.principal = True

    db.session.commit()

    try:
        if ruta_archivo.is_file():
            ruta_archivo.unlink()

    except OSError as error:
        print(
            f"No se pudo borrar el archivo "
            f"{ruta_archivo}: {error}"
        )

    return redirect(
        url_for(
            "administrar_fotos",
            sorteo_id=sorteo.id
        )
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/participantes"
)
@admin_requerido
def admin_participantes(sorteo_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    participaciones = Participacion.query.filter_by(
        sorteo_id=sorteo.id
    ).order_by(
        Participacion.fecha_creacion.desc()
    ).all()

    datos = []

    for participacion in participaciones:

        numeros = Numero.query.filter_by(
            participacion_id=participacion.id
        ).order_by(
            Numero.numero
        ).all()

        pago = Pago.query.filter_by(
            participacion_id=participacion.id
        ).first()

        datos.append({
            "participacion": participacion,
            "numeros": numeros,
            "pago": pago
        })

    disponibles = Numero.query.filter_by(
        sorteo_id=sorteo.id,
        estado="disponible"
    ).count()

    reservados = Numero.query.filter_by(
        sorteo_id=sorteo.id,
        estado="reservado"
    ).count()

    vendidos = Numero.query.filter_by(
        sorteo_id=sorteo.id,
        estado="vendido"
    ).count()

    confirmadas = Participacion.query.filter_by(
        sorteo_id=sorteo.id,
        estado="confirmada"
    ).count()

    revision = Participacion.query.filter_by(
        sorteo_id=sorteo.id,
        estado="requiere_revision"
    ).count()

    pagos_aprobados = (
        db.session.query(Pago)
        .join(
            Participacion,
            Pago.participacion_id == Participacion.id
        )
        .filter(
            Participacion.sorteo_id == sorteo.id,
            Pago.estado == "aprobado"
        )
        .all()
    )

    recaudado = sum(
        pago.monto
        for pago in pagos_aprobados
    )

    estadisticas = {
        "disponibles": disponibles,
        "reservados": reservados,
        "vendidos": vendidos,
        "confirmadas": confirmadas,
        "revision": revision,
        "recaudado": recaudado
    }

    return render_template(
        "admin_participantes.html",
        sorteo=sorteo,
        datos=datos,
        estadisticas=estadisticas
    )


@app.route(
    "/admin/sorteos/<int:sorteo_id>/packs",
    methods=["GET", "POST"]
)
@admin_requerido
def administrar_packs(sorteo_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        try:
            cantidad = int(
                request.form.get("cantidad", "0")
            )

            precio = float(
                request.form.get("precio", "0")
            )

        except ValueError:
            return "Cantidad o precio inválido.", 400

        if not nombre:
            return "El nombre del pack es obligatorio.", 400

        if cantidad < 1:
            return "La cantidad debe ser mayor a 0.", 400

        if cantidad > sorteo.cantidad_numeros:
            return (
                "El pack no puede superar la cantidad "
                "total de números del sorteo.",
                400
            )

        if precio <= 0:
            return "El precio debe ser mayor a 0.", 400

        ultimo_orden = (
            db.session.query(db.func.max(Pack.orden))
            .filter_by(sorteo_id=sorteo.id)
            .scalar()
        )

        nuevo_pack = Pack(
            nombre=nombre,
            cantidad=cantidad,
            precio=precio,
            activo=True,
            orden=(ultimo_orden or 0) + 1,
            sorteo_id=sorteo.id
        )

        db.session.add(nuevo_pack)
        db.session.commit()

        return redirect(
            url_for(
                "administrar_packs",
                sorteo_id=sorteo.id
            )
        )

    return render_template(
        "admin_packs.html",
        sorteo=sorteo
    )


@app.route(
    "/admin/packs/<int:pack_id>/editar",
    methods=["GET", "POST"]
)
@admin_requerido
def editar_pack(pack_id):

    pack = Pack.query.get_or_404(pack_id)
    sorteo = pack.sorteo

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        try:
            cantidad = int(
                request.form.get("cantidad", "0")
            )

            precio = float(
                request.form.get("precio", "0")
            )

        except ValueError:
            return "Cantidad o precio inválido.", 400

        if not nombre:
            return "El nombre del pack es obligatorio.", 400

        if cantidad < 1:
            return "La cantidad debe ser mayor a 0.", 400

        if cantidad > sorteo.cantidad_numeros:
            return (
                "El pack no puede superar la cantidad "
                "total de números del sorteo.",
                400
            )

        if precio <= 0:
            return "El precio debe ser mayor a 0.", 400

        pack.nombre = nombre
        pack.cantidad = cantidad
        pack.precio = precio

        db.session.commit()

        return redirect(
            url_for(
                "administrar_packs",
                sorteo_id=sorteo.id
            )
        )

    return render_template(
        "editar_pack.html",
        pack=pack,
        sorteo=sorteo
    )


@app.route(
    "/admin/packs/<int:pack_id>/estado",
    methods=["POST"]
)
@admin_requerido
def cambiar_estado_pack(pack_id):

    pack = Pack.query.get_or_404(pack_id)

    pack.activo = not pack.activo

    db.session.commit()

    return redirect(
        url_for(
            "administrar_packs",
            sorteo_id=pack.sorteo_id
        )
    )


@app.route(
    "/admin/packs/<int:pack_id>/eliminar",
    methods=["POST"]
)
@admin_requerido
def eliminar_pack(pack_id):

    pack = Pack.query.get_or_404(pack_id)
    sorteo_id = pack.sorteo_id

    db.session.delete(pack)
    db.session.commit()

    return redirect(
        url_for(
            "administrar_packs",
            sorteo_id=sorteo_id
        )
    )


@app.route("/admin/sorteos/nuevo", methods=["GET", "POST"])
@admin_requerido
def nuevo_sorteo():

    if request.method == "POST":

        titulo = request.form["titulo"].strip()
        descripcion = request.form["descripcion"].strip()

        try:
            cantidad_numeros = int(
                request.form["cantidad_numeros"]
            )
        except (ValueError, TypeError):
            return "Cantidad de números inválida.", 400

        if not titulo:
            return "El título es obligatorio.", 400

        if cantidad_numeros < 1:
            return (
                "La cantidad de números debe ser "
                "mayor a 0.",
                400
            )

        nuevo = Sorteo(
            titulo=titulo,
            descripcion=descripcion,

            # Valores heredados. La compra actual
            # utiliza los precios y cantidades
            # configurados en los packs.
            precio_numero=1,
            max_numeros_por_persona=1,

            cantidad_numeros=cantidad_numeros,
            activo=True
        )

        db.session.add(nuevo)
        db.session.commit()

        for i in range(
            1,
            nuevo.cantidad_numeros + 1
        ):

            numero = Numero(
                numero=i,
                sorteo_id=nuevo.id
            )

            db.session.add(numero)

        db.session.commit()

        # Guardar imágenes del sorteo
        imagenes = request.files.getlist("imagenes")

        orden = 0

        for imagen in imagenes:

            if not imagen or not imagen.filename:
                continue

            try:
                ruta_imagen = guardar_imagen(
                    imagen,
                    nuevo.id
                )

                multimedia = Multimedia(
                    sorteo_id=nuevo.id,
                    tipo="imagen",
                    url=ruta_imagen,
                    principal=(orden == 0),
                    orden=orden
                )

                db.session.add(multimedia)

                orden += 1

            except ValueError as error:
                print(
                    f"No se pudo guardar una imagen: {error}"
                )

        db.session.commit()

        return "Sorteo creado correctamente"

    return render_template(
        "nuevo_sorteo.html"
    )


@app.route("/participar/<int:sorteo_id>", methods=["GET", "POST"])
def participar(sorteo_id):

    sorteo = Sorteo.query.get_or_404(sorteo_id)

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()

        if not nombre:
            return "El nombre es obligatorio.", 400

        if not email:
            return "El email es obligatorio.", 400

        if not telefono:
            return "El teléfono es obligatorio.", 400

        try:
            pack_id = int(
                request.form.get("pack_id", "")
            )
        except (TypeError, ValueError):
            return "El pack seleccionado no es válido.", 400

        pack = Pack.query.filter_by(
            id=pack_id,
            sorteo_id=sorteo.id,
            activo=True
        ).first()

        if pack is None:
            return (
                "El pack seleccionado no existe "
                "o ya no está disponible.",
                400
            )

        cantidad = pack.cantidad

        if cantidad < 1:
            return "El pack tiene una cantidad inválida.", 400

        numeros_disponibles = Numero.query.filter_by(
            sorteo_id=sorteo.id,
            estado="disponible"
        ).all()

        if len(numeros_disponibles) < cantidad:
            return "No hay suficientes números disponibles."

        numeros_asignados = random.sample(
            numeros_disponibles,
            cantidad
        )

        participacion = Participacion(
            nombre=nombre,
            email=email,
            telefono=telefono,
            cantidad=cantidad,
            pack_nombre=pack.nombre,
            pack_precio=pack.precio,
            estado="reservado",
            fecha_expiracion=ahora_utc() + timedelta(minutes=15),
            sorteo_id=sorteo.id
        )

        db.session.add(participacion)

        db.session.flush()

        for numero in numeros_asignados:

            numero.estado = "reservado"
            numero.participacion_id = participacion.id

        pago = Pago(
            participacion_id=participacion.id,
            monto=pack.precio,
            estado="pendiente",
            metodo="mercado_pago"
        )

        db.session.add(pago)

        db.session.commit()

        try:
            respuesta_mp = crear_preferencia(
                f"{sorteo.titulo} - {pack.nombre}",
                1,
                pack.precio,
                participacion.id
            )

            datos_mp = (
                respuesta_mp.get("response")
                if isinstance(respuesta_mp, dict)
                else None
            )

            if not isinstance(datos_mp, dict):
                raise ValueError(
                    "Mercado Pago no devolvió una respuesta válida."
                )

            preferencia_id = datos_mp.get("id")
            checkout_url = datos_mp.get("init_point")

            if not preferencia_id or not checkout_url:
                raise ValueError(
                    "Mercado Pago no devolvió los datos "
                    "necesarios para iniciar el pago."
                )

            pago.preferencia_id = preferencia_id

            db.session.commit()

        except Exception as error:

            print(
                "MERCADO PAGO: no se pudo crear "
                f"la preferencia: {error}"
            )

            for numero in numeros_asignados:
                numero.estado = "disponible"
                numero.participacion_id = None

            participacion.estado = "vencido"
            participacion.fecha_expiracion = ahora_utc()

            pago.estado = "cancelado"

            db.session.commit()

            return (
                "No pudimos iniciar el pago con Mercado Pago. "
                "Tus números fueron liberados para que puedas "
                "intentarlo nuevamente.",
                503
            )

        numeros = [
            numero.numero
            for numero in numeros_asignados
        ]

        return render_template(
            "resultado_asignacion.html",
            sorteo=sorteo,
            participacion=participacion,
            numeros=numeros,
            checkout_url=checkout_url
        )

    return render_template(
        "participar.html",
        sorteo=sorteo
    )


@app.route(
    "/admin/participaciones/<int:participacion_id>/asignar-numeros",
    methods=["POST"]
)
@admin_requerido
def asignar_numeros_revision(participacion_id):

    participacion = db.session.get(
        Participacion,
        participacion_id
    )

    if participacion is None:
        return "Participación no encontrada.", 404

    if participacion.estado != "requiere_revision":
        return (
            "Esta participación ya no requiere revisión.",
            400
        )

    pago = Pago.query.filter_by(
        participacion_id=participacion.id
    ).first()

    if not pago or pago.estado != "aprobado":
        return (
            "No existe un pago aprobado para esta participación.",
            400
        )

    sorteo = Sorteo.query.get_or_404(
        participacion.sorteo_id
    )

    disponibles = Numero.query.filter_by(
        sorteo_id=sorteo.id,
        estado="disponible"
    ).count()

    if disponibles < participacion.cantidad:
        return (
            "No hay suficientes números disponibles "
            "para resolver esta participación.",
            400
        )

    numeros_disponibles = Numero.query.filter_by(
        sorteo_id=sorteo.id,
        estado="disponible"
    ).all()

    if len(numeros_disponibles) < participacion.cantidad:
        return (
            "No hay suficientes números disponibles.",
            400
        )

    numeros_asignados = random.sample(
        numeros_disponibles,
        participacion.cantidad
    )

    for numero in numeros_asignados:
        numero.estado = "vendido"
        numero.participacion_id = participacion.id

    participacion.estado = "confirmada"
    participacion.fecha_expiracion = None

    db.session.commit()

    # La participación ya quedó confirmada y guardada.
    # Ahora enviamos el correo con los nuevos números.
    try:
        from servicios.email import (
            preparar_confirmacion_pago,
            enviar_email,
        )

        datos_email = preparar_confirmacion_pago(
            participacion
        )

        enviado = enviar_email(
            destinatario=datos_email["destinatario"],
            asunto=datos_email["asunto"],
            contenido_html=datos_email["html"],
        )

        if enviado:
            print(
                f"Email de confirmación enviado "
                f"para la participación "
                f"{participacion.id} "
                f"resuelta manualmente."
            )
        else:
            print(
                f"No se pudo enviar el email "
                f"de la participación "
                f"{participacion.id}."
            )

    except Exception as error:
        print(
            f"Error enviando email de la "
            f"participación {participacion.id}: "
            f"{error}"
        )

    return redirect(
        url_for(
            "admin_participantes",
            sorteo_id=sorteo.id
        )
    )


@app.route("/webhook/mercadopago", methods=["POST"])
@csrf.exempt
def webhook_mercadopago():

    datos = request.get_json(silent=True) or {}

    print(
        "Webhook recibido:",
        datos.get("type"),
        datos.get("data", {}).get("id")
    )

    tipo = datos.get("type") or request.args.get("type")

    if tipo != "payment":
        return "OK", 200

    id_pago = (
        datos.get("data", {}).get("id")
        or request.args.get("data.id")
    )

    if not id_pago:
        print("Webhook sin ID de pago.")
        return "OK", 200

    x_signature = request.headers.get("x-signature")
    x_request_id = request.headers.get("x-request-id")

    from servicios.validar_webhook import validar_webhook

    firma_valida = validar_webhook(
        x_signature,
        x_request_id,
        str(id_pago)
    )

    if not firma_valida:
        print(
            f"Firma de webhook inválida para el pago {id_pago}."
        )
        return "Firma inválida", 401

    print(
        f"Firma de webhook válida para el pago {id_pago}."
    )

    respuesta = consultar_pago(id_pago)

    if respuesta["status"] != 200:
        print(
            f"No se pudo consultar el pago {id_pago}."
        )
        return "OK", 200

    pago_mp = respuesta["response"]

    print(
        "Estado Mercado Pago:",
        pago_mp.get("status")
    )

    print(
        "Referencia:",
        pago_mp.get("external_reference")
    )

    try:
        procesar_pago_aprobado(
            id_pago,
            pago_mp
        )

    except Exception as e:
        print(
            f"Error procesando el pago {id_pago}:",
            e
        )

        db.session.rollback()

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
