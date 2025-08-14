def _procesar_productos(self, productos_data, precios_data):
    """Procesa productos y precios con validación estricta y logs de depuración"""
    ProductProduct = self.env['product.product']
    contador = 0

    # Estructurar precios por código
    precios_por_kopr = {}
    for item in precios_data:
        _logger.info("Item de precios: %s", item)  # log de depuración
        if not isinstance(item, dict) or item.get('error'):
            continue

        kopr_precio = (item.get('kopr') or '').replace(' ', '').upper()
        if not kopr_precio:
            continue

        # Procesar unidades para obtener precios
        for unidad in item.get('unidades', []):
            if not isinstance(unidad, dict):
                continue

            precio_neto = self._extraer_precio(unidad.get('prunneto'))
            precio_bruto = self._extraer_precio(unidad.get('prunbruto'))

            if precio_neto is not None and precio_bruto is not None:
                precios_por_kopr[kopr_precio] = {
                    'neto': precio_neto,
                    'bruto': precio_bruto,
                    'unidad': unidad.get('nombre'),
                    'fraccionable': unidad.get('fraccionable', False)
                }
                break  # usar la primera unidad con precios válidos

    _logger.info("Precios obtenidos para %d productos", len(precios_por_kopr))

    # Procesar productos
    for item in productos_data:
        _logger.info("Item de productos: %s", item)  # log de depuración
        if not isinstance(item, dict):
            continue

        kopr_producto = (item.get('KOPR') or '').replace(' ', '').upper()
        nokopr = item.get('NOKOPR')

        if not kopr_producto or not nokopr:
            continue

        if kopr_producto in precios_por_kopr:
            try:
                precio_info = precios_por_kopr[kopr_producto]
                producto = ProductProduct.search([('barcode', '=', kopr_producto)], limit=1)

                vals = {
                    'name': nokopr,
                    'lst_price': precio_info['neto'],
                    'sales_price': precio_info['bruto'],
                    'barcode': kopr_producto,
                    'default_code': kopr_producto,
                    'type': 'product' if precio_info['fraccionable'] else 'consu',
                    'sale_ok': True,
                    'purchase_ok': True,
                    'standard_price': precio_info['neto'],  # Costo = precio neto
                    'uom_id': self._obtener_unidad(precio_info['unidad']),
                    'uom_po_id': self._obtener_unidad(precio_info['unidad'])
                }

                if not producto:
                    ProductProduct.create(vals)
                else:
                    producto.write(vals)

                contador += 1
                _logger.debug("Procesado %s: %s", kopr_producto, nokopr)

            except Exception as e:
                _logger.error("Error procesando %s: %s", kopr_producto, str(e))

    # Resultado
    if contador == 0:
        msg = "No se encontraron productos con precios válidos" if productos_data else "No hay productos para importar"
        _logger.error(msg)
        raise UserError(msg)

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Éxito',
            'message': f'{contador} productos procesados correctamente',
            'type': 'success',
            'sticky': False,
        }
    }
