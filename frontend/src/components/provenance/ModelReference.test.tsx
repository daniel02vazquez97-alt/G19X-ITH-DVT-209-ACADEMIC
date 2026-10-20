import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ModelReference } from './ModelReference';

describe('ModelReference (U14, DT-104)', () => {
  it('shows the Azure ML registry entry of the reference baseline', () => {
    const { container } = render(
      <ModelReference
        model={{
          name: 'baseline.moving_average',
          version: '1.0.0',
          external_ref: 'azureml:baseline-ma13:1',
        }}
      />,
    );
    expect(container.textContent).toBe(
      'baseline.moving_average 1.0.0 · registrado y validado en Azure ML como azureml:baseline-ma13:1',
    );
    expect(screen.getByText('azureml:baseline-ma13:1').tagName).toBe('CODE');
  });

  it('without a registry entry it shows only the model, and a dash without a model', () => {
    const { container, rerender } = render(
      <ModelReference model={{ name: 'baseline.naive', version: '1.0.0', external_ref: null }} />,
    );
    expect(container.textContent).toBe('baseline.naive 1.0.0');
    rerender(<ModelReference model={null} />);
    expect(container.textContent).toBe('—');
  });
});
